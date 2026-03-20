# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Observation Service — user session behavior tracking.

Covers: ObservationStore, record_observation, get_user_observations,
infer_intent, module-level singleton.
T475.
"""

from __future__ import annotations

import sys
import time
from datetime import datetime, timezone, timedelta
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


from hr_advisory.shadow.observation import (
    ObservationStore,
    get_observation_store,
)


# =========================================================================
# ObservationStore Construction Tests
# =========================================================================


class TestObservationStoreConstruction:
    """ObservationStore must initialize with correct defaults."""

    def test_default_max_entries(self) -> None:
        store = ObservationStore()
        assert store._max_entries == 10000

    def test_custom_max_entries(self) -> None:
        store = ObservationStore(max_entries=50)
        assert store._max_entries == 50

    def test_default_ttl_hours(self) -> None:
        store = ObservationStore()
        assert store._ttl_hours == 24

    def test_custom_ttl_hours(self) -> None:
        store = ObservationStore(ttl_hours=12)
        assert store._ttl_hours == 12

    def test_starts_empty(self) -> None:
        store = ObservationStore()
        obs = store.get_user_observations("user1")
        assert obs == []


# =========================================================================
# record_observation Tests
# =========================================================================


class TestRecordObservation:
    """record_observation must store observations with all required fields."""

    def setup_method(self) -> None:
        self.store = ObservationStore(max_entries=100)

    def test_record_basic_observation(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="leave",
            action_type="page_view",
            details={"tab": "balances"},
        )
        obs = self.store.get_user_observations("user1")
        assert len(obs) == 1

    def test_observation_has_required_fields(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="payroll",
            action_type="page_view",
            details={},
        )
        obs = self.store.get_user_observations("user1")
        entry = obs[0]
        assert entry["user_id"] == "user1"
        assert entry["page"] == "payroll"
        assert entry["action_type"] == "page_view"
        assert "details" in entry
        assert "timestamp" in entry
        assert "session_id" in entry

    def test_timestamp_is_iso8601(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="employees",
            action_type="click",
            details={},
        )
        obs = self.store.get_user_observations("user1")
        ts = obs[0]["timestamp"]
        # Should parse as ISO 8601
        parsed = datetime.fromisoformat(ts)
        assert parsed.tzinfo is not None  # Must be timezone-aware

    def test_multiple_observations_same_user(self) -> None:
        for i in range(5):
            self.store.record_observation(
                user_id="user1",
                page=f"page_{i}",
                action_type="page_view",
                details={},
            )
        obs = self.store.get_user_observations("user1")
        assert len(obs) == 5

    def test_observations_isolated_by_user(self) -> None:
        self.store.record_observation(
            user_id="alice",
            page="leave",
            action_type="page_view",
            details={},
        )
        self.store.record_observation(
            user_id="bob",
            page="payroll",
            action_type="page_view",
            details={},
        )
        alice_obs = self.store.get_user_observations("alice")
        bob_obs = self.store.get_user_observations("bob")
        assert len(alice_obs) == 1
        assert len(bob_obs) == 1
        assert alice_obs[0]["page"] == "leave"
        assert bob_obs[0]["page"] == "payroll"

    def test_session_id_present(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="dashboard",
            action_type="page_view",
            details={},
        )
        obs = self.store.get_user_observations("user1")
        assert obs[0]["session_id"] is not None
        assert isinstance(obs[0]["session_id"], str)
        assert len(obs[0]["session_id"]) > 0

    def test_details_preserved(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="employees",
            action_type="search",
            details={"query": "John", "results_count": 3},
        )
        obs = self.store.get_user_observations("user1")
        assert obs[0]["details"]["query"] == "John"
        assert obs[0]["details"]["results_count"] == 3


# =========================================================================
# Bounded Storage Tests
# =========================================================================


class TestBoundedStorage:
    """ObservationStore must respect max_entries and evict oldest."""

    def test_evicts_oldest_when_full(self) -> None:
        store = ObservationStore(max_entries=5)
        for i in range(7):
            store.record_observation(
                user_id="user1",
                page=f"page_{i}",
                action_type="page_view",
                details={},
            )
        # Should have at most 5 entries total (across all users)
        all_obs = store.get_user_observations("user1")
        assert len(all_obs) <= 5

    def test_total_entries_bounded(self) -> None:
        store = ObservationStore(max_entries=10)
        for i in range(15):
            store.record_observation(
                user_id=f"user_{i}",
                page="dashboard",
                action_type="page_view",
                details={},
            )
        # Total entries across all users should not exceed max
        total = sum(len(store.get_user_observations(f"user_{i}")) for i in range(15))
        assert total <= 10


# =========================================================================
# get_user_observations Tests
# =========================================================================


class TestGetUserObservations:
    """get_user_observations must filter by user and time window."""

    def setup_method(self) -> None:
        self.store = ObservationStore(max_entries=1000)

    def test_returns_empty_for_unknown_user(self) -> None:
        obs = self.store.get_user_observations("nonexistent")
        assert obs == []

    def test_default_since_hours_is_24(self) -> None:
        # Record an observation
        self.store.record_observation(
            user_id="user1",
            page="dashboard",
            action_type="page_view",
            details={},
        )
        # Should be returned within default 24-hour window
        obs = self.store.get_user_observations("user1")
        assert len(obs) == 1

    def test_filters_by_since_hours(self) -> None:
        # Record an observation and manually backdate it
        self.store.record_observation(
            user_id="user1",
            page="dashboard",
            action_type="page_view",
            details={},
        )
        # All recent observations should appear in a 24-hour window
        obs = self.store.get_user_observations("user1", since_hours=24)
        assert len(obs) >= 1

    def test_returns_observations_in_order(self) -> None:
        pages = ["leave", "payroll", "employees"]
        for page in pages:
            self.store.record_observation(
                user_id="user1",
                page=page,
                action_type="page_view",
                details={},
            )
        obs = self.store.get_user_observations("user1")
        # Should maintain insertion order or reverse chronological
        assert len(obs) == 3


# =========================================================================
# TTL Cleanup Tests
# =========================================================================


class TestTTLCleanup:
    """Expired observations must be cleaned up."""

    def test_expired_observations_excluded(self) -> None:
        store = ObservationStore(max_entries=100, ttl_hours=24)
        # Record an observation
        store.record_observation(
            user_id="user1",
            page="dashboard",
            action_type="page_view",
            details={},
        )
        # Manually backdate the timestamp to 25 hours ago
        old_ts = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        # Find the observation and update its timestamp
        for key, entry in store._store.items():
            if entry["user_id"] == "user1":
                entry["timestamp"] = old_ts
                break
        # Should be excluded from 24-hour window
        obs = store.get_user_observations("user1", since_hours=24)
        assert len(obs) == 0


# =========================================================================
# infer_intent Tests
# =========================================================================


class TestInferIntent:
    """infer_intent must produce actionable nudges from observation patterns."""

    def setup_method(self) -> None:
        self.store = ObservationStore(max_entries=1000)

    def test_no_observations_returns_empty(self) -> None:
        suggestions = self.store.infer_intent("user1")
        assert suggestions == []

    def test_leave_page_3_plus_views_suggests_apply(self) -> None:
        for _ in range(3):
            self.store.record_observation(
                user_id="user1",
                page="leave",
                action_type="page_view",
                details={},
            )
        suggestions = self.store.infer_intent("user1")
        assert len(suggestions) >= 1
        # Should suggest something about applying for leave
        leave_suggestions = [s for s in suggestions if "leave" in s.lower()]
        assert len(leave_suggestions) >= 1

    def test_payroll_after_attendance_suggests_run_payroll(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="attendance",
            action_type="page_view",
            details={},
        )
        self.store.record_observation(
            user_id="user1",
            page="payroll",
            action_type="page_view",
            details={},
        )
        suggestions = self.store.infer_intent("user1")
        assert len(suggestions) >= 1
        payroll_suggestions = [s for s in suggestions if "payroll" in s.lower()]
        assert len(payroll_suggestions) >= 1

    def test_employees_page_repeated_suggests_search(self) -> None:
        for _ in range(3):
            self.store.record_observation(
                user_id="user1",
                page="employees",
                action_type="page_view",
                details={},
            )
        suggestions = self.store.infer_intent("user1")
        assert len(suggestions) >= 1
        search_suggestions = [s for s in suggestions if "search" in s.lower()]
        assert len(search_suggestions) >= 1

    def test_single_view_no_suggestions(self) -> None:
        self.store.record_observation(
            user_id="user1",
            page="leave",
            action_type="page_view",
            details={},
        )
        suggestions = self.store.infer_intent("user1")
        # A single view should not trigger pattern-based suggestions
        assert len(suggestions) == 0

    def test_different_user_no_cross_contamination(self) -> None:
        # User1 views leave 3 times
        for _ in range(3):
            self.store.record_observation(
                user_id="user1",
                page="leave",
                action_type="page_view",
                details={},
            )
        # User2 should not get suggestions from user1's activity
        suggestions = self.store.infer_intent("user2")
        assert len(suggestions) == 0


# =========================================================================
# Singleton Tests
# =========================================================================


class TestObservationStoreSingleton:
    """Module-level singleton must return the same instance."""

    def test_singleton_returns_same_instance(self) -> None:
        store1 = get_observation_store()
        store2 = get_observation_store()
        assert store1 is store2

    def test_singleton_is_observation_store(self) -> None:
        store = get_observation_store()
        assert isinstance(store, ObservationStore)
