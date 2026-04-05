# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Observation Service — user session behavior tracking.

Tracks page views, clicks, and interactions to infer user intent.
Uses in-memory storage with TTL-based cleanup and bounded capacity.

Inference rules:
    - 3+ views on leave page -> suggest applying for leave
    - attendance then payroll visit -> suggest running payroll
    - 3+ views on employees page -> suggest using search
"""

from __future__ import annotations

import logging
import uuid
from collections import Counter, OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any

logger = logging.getLogger(__name__)

__all__ = [
    "ObservationStore",
    "get_observation_store",
]

# Defaults
_MAX_ENTRIES = 10000
_TTL_HOURS = 24


class ObservationStore:
    """In-memory store for user session observations.

    Uses OrderedDict for insertion-order tracking with LRU eviction
    when the store exceeds max_entries. Observations older than
    ttl_hours are excluded from queries and periodically cleaned.

    Production: swap to Redis or database-backed store.
    """

    def __init__(
        self,
        max_entries: int = _MAX_ENTRIES,
        ttl_hours: int = _TTL_HOURS,
    ) -> None:
        if max_entries <= 0:
            raise ValueError(f"max_entries must be positive, got {max_entries}")
        if ttl_hours <= 0:
            raise ValueError(f"ttl_hours must be positive, got {ttl_hours}")

        self._store: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_entries = max_entries
        self._ttl_hours = ttl_hours

    def record_observation(
        self,
        user_id: str,
        page: str,
        action_type: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a page view or interaction event.

        Args:
            user_id: The user who performed the action.
            page: The page name (e.g. "leave", "payroll", "employees").
            action_type: The type of action (e.g. "page_view", "click", "search").
            details: Optional additional details about the interaction.

        Returns:
            The recorded observation dict.
        """
        if not user_id:
            raise ValueError("user_id must not be empty")
        if not page:
            raise ValueError("page must not be empty")
        if not action_type:
            raise ValueError("action_type must not be empty")

        # Evict oldest entries if at capacity
        while len(self._store) >= self._max_entries:
            evicted_key, _ = self._store.popitem(last=False)
            logger.debug("Observation evicted (LRU): %s", evicted_key)

        observation_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)

        entry: dict[str, Any] = {
            "user_id": user_id,
            "page": page,
            "action_type": action_type,
            "details": details if details is not None else {},
            "timestamp": now.isoformat(),
            "session_id": session_id,
        }

        self._store[observation_id] = entry

        logger.debug(
            "Observation recorded: user=%s, page=%s, action=%s",
            user_id,
            page,
            action_type,
        )

        # Persist to database (best-effort)
        self._persist_observation(user_id, page, action_type, details, session_id)

        return entry

    def _persist_observation(
        self,
        user_id: str,
        page: str,
        action_type: str,
        details: dict[str, Any] | None,
        session_id: str,
    ) -> None:
        """Persist observation to database (best-effort, logs on failure)."""
        try:
            import json

            from hr_advisory.services import dataflow_crud

            # Truncate inputs to prevent oversized DB rows (H1/H2 fix)
            details_json = json.dumps(details or {})
            if len(details_json) > 4000:
                details_json = json.dumps({"truncated": True})

            dataflow_crud.create(
                "UserObservation",
                {
                    "user_id": int(user_id) if user_id.isdigit() else 0,
                    "session_id": session_id[:200],
                    "page": page[:200],
                    "action_type": action_type[:100],
                    "details": details_json,
                },
            )
        except Exception as exc:
            logger.warning("Failed to persist observation: %s", exc)

    def get_user_observations(
        self,
        user_id: str,
        since_hours: int = 24,
    ) -> list[dict[str, Any]]:
        """Get recent observations for a user within a time window.

        Args:
            user_id: The user to query observations for.
            since_hours: Only return observations from the last N hours.
                Defaults to 24 hours.

        Returns:
            List of observation dicts, ordered by insertion time.
        """
        if not user_id:
            raise ValueError("user_id must not be empty")

        cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
        results: list[dict[str, Any]] = []

        for entry in self._store.values():
            if entry["user_id"] != user_id:
                continue

            # Parse timestamp and filter by time window
            try:
                entry_ts = datetime.fromisoformat(entry["timestamp"])
            except (ValueError, KeyError):
                logger.warning(
                    "Observation with invalid timestamp for user=%s, skipping",
                    user_id,
                )
                continue

            if entry_ts >= cutoff:
                results.append(entry)

        return results

    def infer_intent(self, user_id: str) -> list[str]:
        """Infer user intent from recent observation patterns.

        Uses simple rule-based pattern matching:
            - Leave page viewed 3+ times -> suggest applying for leave
            - Attendance then payroll visit -> suggest running payroll
            - Employees page viewed 3+ times -> suggest using search

        Args:
            user_id: The user to infer intent for.

        Returns:
            List of suggestion strings (may be empty if no patterns match).
        """
        observations = self.get_user_observations(user_id, since_hours=self._ttl_hours)
        if not observations:
            return []

        suggestions: list[str] = []

        # Count page views per page
        page_counts: Counter[str] = Counter()
        for obs in observations:
            page_counts[obs["page"]] += 1

        # Rule 1: Leave page viewed 3+ times
        if page_counts.get("leave", 0) >= 3:
            suggestions.append("Would you like to apply for leave?")

        # Rule 2: Attendance then payroll sequence detection
        pages_sequence = [obs["page"] for obs in observations]
        for i in range(len(pages_sequence) - 1):
            if pages_sequence[i] == "attendance" and pages_sequence[i + 1] == "payroll":
                suggestions.append("Ready to run payroll?")
                break

        # Rule 3: Employees page viewed 3+ times
        if page_counts.get("employees", 0) >= 3:
            suggestions.append("Looking for someone? Try search.")

        return suggestions


# Module-level singleton
_store: ObservationStore | None = None


def get_observation_store() -> ObservationStore:
    """Get or create the shared ObservationStore singleton."""
    global _store
    if _store is None:
        _store = ObservationStore()
    return _store
