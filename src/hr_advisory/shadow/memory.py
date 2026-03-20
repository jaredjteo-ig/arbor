# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Memory Distillation Service — compresses observations into preferences.

Takes raw session observations and distills them into a compact
user memory containing themes, patterns, and preferences. This
memory persists across sessions and powers personalized nudges.

Distillation rules:
    - Themes: "You've been focused on payroll this week" (count by module)
    - Patterns: "You always check attendance before payroll" (sequences)
    - Preferences: top 3 most-used pages
"""

from __future__ import annotations

import logging
from collections import Counter, OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "MemoryStore",
    "UserMemory",
    "get_memory_store",
]

# Defaults
_MAX_PREFERENCES_PER_USER = 200

# Known page sequences that indicate workflows
_KNOWN_SEQUENCES: list[tuple[str, str, str]] = [
    ("attendance", "payroll", "You always check attendance before payroll"),
    ("employees", "payroll", "You review employees before running payroll"),
    ("leave", "attendance", "You check leave before reviewing attendance"),
    ("payroll", "documents", "You generate documents after payroll"),
    ("dashboard", "employees", "You check employee details from the dashboard"),
]


@dataclass
class UserMemory:
    """Distilled memory for a single user.

    Attributes:
        themes: High-level behavioral themes (e.g. "focused on payroll").
        patterns: Detected action sequences (e.g. "checks attendance before payroll").
        preferences: Key-value preferences (e.g. top pages, favorite actions).
        last_distilled: ISO 8601 timestamp of the last distillation.
    """

    themes: list[str]
    patterns: list[str]
    preferences: dict[str, Any]
    last_distilled: str

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict for JSON responses."""
        return {
            "themes": self.themes,
            "patterns": self.patterns,
            "preferences": self.preferences,
            "last_distilled": self.last_distilled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> UserMemory:
        """Deserialize from a plain dict."""
        return cls(
            themes=data.get("themes", []),
            patterns=data.get("patterns", []),
            preferences=data.get("preferences", {}),
            last_distilled=data.get("last_distilled", ""),
        )


class MemoryStore:
    """In-memory store for distilled user memories.

    Stores up to max_preferences_per_user preference entries per user.
    Production: swap to database-backed store.
    """

    def __init__(
        self,
        max_preferences_per_user: int = _MAX_PREFERENCES_PER_USER,
    ) -> None:
        if max_preferences_per_user <= 0:
            raise ValueError(
                f"max_preferences_per_user must be positive, got {max_preferences_per_user}"
            )

        self._memories: OrderedDict[str, UserMemory] = OrderedDict()
        self._max_preferences_per_user = max_preferences_per_user
        self._max_users = 10000

    def distill(
        self,
        user_id: str,
        observations: list[dict[str, Any]],
    ) -> UserMemory:
        """Distill raw observations into a compact user memory.

        Extracts themes (module focus), patterns (action sequences),
        and preferences (top pages) from the observation list. Replaces
        any existing memory for this user.

        Args:
            user_id: The user to distill memory for.
            observations: List of observation dicts with keys:
                user_id, page, action_type, details, timestamp, session_id.

        Returns:
            The distilled UserMemory.
        """
        if not user_id:
            raise ValueError("user_id must not be empty")

        # LRU eviction
        while len(self._memories) >= self._max_users and user_id not in self._memories:
            self._memories.popitem(last=False)
        if user_id in self._memories:
            self._memories.move_to_end(user_id)

        if not observations:
            memory = UserMemory(
                themes=[],
                patterns=[],
                preferences={},
                last_distilled=datetime.now(timezone.utc).isoformat(),
            )
            self._memories[user_id] = memory
            logger.debug("Distilled empty memory for user=%s", user_id)
            return memory

        themes = self._extract_themes(observations)
        patterns = self._extract_patterns(observations)
        preferences = self._extract_preferences(observations)

        memory = UserMemory(
            themes=themes,
            patterns=patterns,
            preferences=preferences,
            last_distilled=datetime.now(timezone.utc).isoformat(),
        )

        self._memories[user_id] = memory

        logger.info(
            "Distilled memory for user=%s: %d themes, %d patterns, %d preferences",
            user_id,
            len(themes),
            len(patterns),
            len(preferences),
        )

        return memory

    def get_memory(self, user_id: str) -> UserMemory:
        """Get the distilled memory for a user.

        Args:
            user_id: The user to retrieve memory for.

        Returns:
            The UserMemory for this user, or an empty default if none exists.
        """
        if not user_id:
            raise ValueError("user_id must not be empty")

        memory = self._memories.get(user_id)
        if memory is None:
            return UserMemory(
                themes=[],
                patterns=[],
                preferences={},
                last_distilled="",
            )
        return memory

    def _extract_themes(
        self,
        observations: list[dict[str, Any]],
    ) -> list[str]:
        """Extract behavioral themes from observations.

        Counts actions by module/page and generates theme statements
        for pages with significant activity (2+ interactions).

        Args:
            observations: The raw observation list.

        Returns:
            List of theme strings.
        """
        page_counts: Counter[str] = Counter()
        for obs in observations:
            page = obs.get("page", "")
            if page:
                page_counts[page] += 1

        themes: list[str] = []
        for page, count in page_counts.most_common():
            if count >= 2:
                themes.append(f"You've been focused on {page} this week")

        return themes

    def _extract_patterns(
        self,
        observations: list[dict[str, Any]],
    ) -> list[str]:
        """Detect action sequences from observations.

        Scans the observation list for known page-to-page transitions
        (e.g. attendance -> payroll) and reports them as patterns.

        Args:
            observations: The raw observation list.

        Returns:
            List of pattern description strings.
        """
        pages = [obs.get("page", "") for obs in observations if obs.get("page")]
        if len(pages) < 2:
            return []

        patterns: list[str] = []
        detected: set[str] = set()

        for i in range(len(pages) - 1):
            current_page = pages[i]
            next_page = pages[i + 1]

            for from_page, to_page, description in _KNOWN_SEQUENCES:
                if current_page == from_page and next_page == to_page:
                    pattern_key = f"{from_page}->{to_page}"
                    if pattern_key not in detected:
                        patterns.append(description)
                        detected.add(pattern_key)

        return patterns

    def _extract_preferences(
        self,
        observations: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Extract top preferences from observations.

        Identifies the top 3 most-visited pages and the top 3
        most-used action types.

        Args:
            observations: The raw observation list.

        Returns:
            Dict with 'top_pages' and 'top_actions' lists.
        """
        page_counts: Counter[str] = Counter()
        action_counts: Counter[str] = Counter()

        for obs in observations:
            page = obs.get("page", "")
            action_type = obs.get("action_type", "")
            if page:
                page_counts[page] += 1
            if action_type:
                action_counts[action_type] += 1

        top_pages = [page for page, _ in page_counts.most_common(3)]
        top_actions = [action for action, _ in action_counts.most_common(3)]

        preferences: dict[str, Any] = {}
        if top_pages:
            preferences["top_pages"] = top_pages
        if top_actions:
            preferences["top_actions"] = top_actions

        return preferences


# Module-level singleton
_store: MemoryStore | None = None


def get_memory_store() -> MemoryStore:
    """Get or create the shared MemoryStore singleton."""
    global _store
    if _store is None:
        _store = MemoryStore()
    return _store
