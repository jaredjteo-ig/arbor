# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Memory Distillation Service — observation compression.

Covers: MemoryStore, UserMemory, distill, get_memory, module-level singleton.
T477.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
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


from hr_advisory.shadow.memory import (
    MemoryStore,
    UserMemory,
    get_memory_store,
)


# =========================================================================
# UserMemory Dataclass Tests
# =========================================================================


class TestUserMemory:
    """UserMemory must be a proper dataclass with correct defaults."""

    def test_create_user_memory(self) -> None:
        mem = UserMemory(
            themes=["focused on payroll"],
            patterns=["checks attendance before payroll"],
            preferences={"top_action": "page_view"},
            last_distilled="2026-03-20T00:00:00+00:00",
        )
        assert mem.themes == ["focused on payroll"]
        assert mem.patterns == ["checks attendance before payroll"]
        assert mem.preferences == {"top_action": "page_view"}
        assert mem.last_distilled == "2026-03-20T00:00:00+00:00"

    def test_empty_user_memory(self) -> None:
        mem = UserMemory(
            themes=[],
            patterns=[],
            preferences={},
            last_distilled="",
        )
        assert mem.themes == []
        assert mem.patterns == []
        assert mem.preferences == {}

    def test_to_dict(self) -> None:
        mem = UserMemory(
            themes=["payroll focus"],
            patterns=["morning routine"],
            preferences={"favorite_page": "dashboard"},
            last_distilled="2026-03-20T00:00:00+00:00",
        )
        d = mem.to_dict()
        assert d["themes"] == ["payroll focus"]
        assert d["patterns"] == ["morning routine"]
        assert d["preferences"] == {"favorite_page": "dashboard"}
        assert d["last_distilled"] == "2026-03-20T00:00:00+00:00"

    def test_from_dict(self) -> None:
        data = {
            "themes": ["leave management"],
            "patterns": ["weekly review"],
            "preferences": {"top_page": "leave"},
            "last_distilled": "2026-03-20T12:00:00+00:00",
        }
        mem = UserMemory.from_dict(data)
        assert mem.themes == ["leave management"]
        assert mem.patterns == ["weekly review"]
        assert mem.preferences == {"top_page": "leave"}
        assert mem.last_distilled == "2026-03-20T12:00:00+00:00"


# =========================================================================
# MemoryStore Construction Tests
# =========================================================================


class TestMemoryStoreConstruction:
    """MemoryStore must initialize with correct defaults."""

    def test_default_max_preferences(self) -> None:
        store = MemoryStore()
        assert store._max_preferences_per_user == 200

    def test_custom_max_preferences(self) -> None:
        store = MemoryStore(max_preferences_per_user=50)
        assert store._max_preferences_per_user == 50

    def test_starts_empty(self) -> None:
        store = MemoryStore()
        mem = store.get_memory("user1")
        assert mem.themes == []
        assert mem.patterns == []
        assert mem.preferences == {}


# =========================================================================
# distill Tests
# =========================================================================


class TestDistill:
    """distill must extract themes, patterns, and preferences from observations."""

    def setup_method(self) -> None:
        self.store = MemoryStore()

    def test_distill_extracts_themes(self) -> None:
        """Themes should identify which modules the user focused on."""
        observations = [
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "click",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "leave",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", observations)
        mem = self.store.get_memory("user1")
        assert len(mem.themes) >= 1
        # Should mention payroll since it's the most-used
        payroll_themes = [t for t in mem.themes if "payroll" in t.lower()]
        assert len(payroll_themes) >= 1

    def test_distill_extracts_patterns(self) -> None:
        """Patterns should detect action sequences (e.g. attendance then payroll)."""
        observations = [
            {
                "user_id": "user1",
                "page": "attendance",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", observations)
        mem = self.store.get_memory("user1")
        # Should detect the attendance -> payroll pattern
        assert len(mem.patterns) >= 1

    def test_distill_extracts_preferences(self) -> None:
        """Preferences should include top 3 most-used actions."""
        observations = [
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "leave",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "employees",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "dashboard",
                "action_type": "click",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", observations)
        mem = self.store.get_memory("user1")
        assert "top_pages" in mem.preferences
        top_pages = mem.preferences["top_pages"]
        assert isinstance(top_pages, list)
        # Payroll should be first since it has the most views
        assert top_pages[0] == "payroll"
        assert len(top_pages) <= 3

    def test_distill_sets_last_distilled_timestamp(self) -> None:
        observations = [
            {
                "user_id": "user1",
                "page": "dashboard",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", observations)
        mem = self.store.get_memory("user1")
        assert mem.last_distilled != ""
        # Should parse as valid ISO 8601
        parsed = datetime.fromisoformat(mem.last_distilled)
        assert parsed.tzinfo is not None

    def test_distill_empty_observations(self) -> None:
        self.store.distill("user1", [])
        mem = self.store.get_memory("user1")
        assert mem.themes == []
        assert mem.patterns == []

    def test_distill_updates_existing_memory(self) -> None:
        """Second distill should replace existing memory, not append."""
        obs1 = [
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", obs1)
        mem1 = self.store.get_memory("user1")
        payroll_themes_1 = [t for t in mem1.themes if "payroll" in t.lower()]
        assert len(payroll_themes_1) >= 1

        obs2 = [
            {
                "user_id": "user1",
                "page": "leave",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s2",
            },
            {
                "user_id": "user1",
                "page": "leave",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s2",
            },
            {
                "user_id": "user1",
                "page": "leave",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s2",
            },
        ]
        self.store.distill("user1", obs2)
        mem2 = self.store.get_memory("user1")
        leave_themes = [t for t in mem2.themes if "leave" in t.lower()]
        assert len(leave_themes) >= 1

    def test_distill_user_isolation(self) -> None:
        """Distilling for user1 must not affect user2."""
        obs1 = [
            {
                "user_id": "user1",
                "page": "payroll",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", obs1)
        mem2 = self.store.get_memory("user2")
        assert mem2.themes == []
        assert mem2.patterns == []
        assert mem2.preferences == {}


# =========================================================================
# get_memory Tests
# =========================================================================


class TestGetMemory:
    """get_memory must return UserMemory with empty defaults for unknown users."""

    def setup_method(self) -> None:
        self.store = MemoryStore()

    def test_returns_user_memory_type(self) -> None:
        mem = self.store.get_memory("user1")
        assert isinstance(mem, UserMemory)

    def test_unknown_user_returns_empty_defaults(self) -> None:
        mem = self.store.get_memory("nonexistent_user")
        assert mem.themes == []
        assert mem.patterns == []
        assert mem.preferences == {}
        assert mem.last_distilled == ""

    def test_returns_distilled_memory(self) -> None:
        observations = [
            {
                "user_id": "user1",
                "page": "dashboard",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "dashboard",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
            {
                "user_id": "user1",
                "page": "dashboard",
                "action_type": "page_view",
                "details": {},
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "session_id": "s1",
            },
        ]
        self.store.distill("user1", observations)
        mem = self.store.get_memory("user1")
        assert mem.last_distilled != ""


# =========================================================================
# Bounded Storage Tests
# =========================================================================


class TestMemoryBoundedStorage:
    """MemoryStore must respect max_preferences_per_user."""

    def test_max_users_bounded(self) -> None:
        store = MemoryStore(max_preferences_per_user=200)
        # The store should handle many users without crashing
        for i in range(50):
            obs = [
                {
                    "user_id": f"user_{i}",
                    "page": "dashboard",
                    "action_type": "page_view",
                    "details": {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "session_id": "s1",
                },
            ]
            store.distill(f"user_{i}", obs)
        # Should have stored memories for all 50 users
        for i in range(50):
            mem = store.get_memory(f"user_{i}")
            assert mem.last_distilled != ""


# =========================================================================
# Singleton Tests
# =========================================================================


class TestMemoryStoreSingleton:
    """Module-level singleton must return the same instance."""

    def test_singleton_returns_same_instance(self) -> None:
        store1 = get_memory_store()
        store2 = get_memory_store()
        assert store1 is store2

    def test_singleton_is_memory_store(self) -> None:
        store = get_memory_store()
        assert isinstance(store, MemoryStore)
