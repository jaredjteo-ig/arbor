"""Long-term memory for per-company patterns and preferences.

Stores frequently asked topics, company-specific context, and
historical advisory patterns. Currently backed by an in-memory
dict; designed to be replaced by a DataFlow persistence backend.
"""

import logging
from collections import Counter
from datetime import datetime
from threading import Lock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class LongTermMemory:
    """Per-company long-term memory.

    Tracks:
      - topic_counts:    how often each domain/topic is asked about
      - company_context: persistent company profile data
      - advisory_history: condensed records of past advisories
    """

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Any]] = {}
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Company context
    # ------------------------------------------------------------------

    def set_company_context(self, company_id: str, context: Dict[str, Any]) -> None:
        """Store or update persistent company context.

        Args:
            company_id: Unique company identifier.
            context: Company profile dict (headcount, sector, etc.).
        """
        with self._lock:
            self._ensure_company(company_id)
            self._store[company_id]["company_context"].update(context)

    def get_company_context(self, company_id: str) -> Dict[str, Any]:
        """Retrieve stored company context."""
        with self._lock:
            self._ensure_company(company_id)
            return dict(self._store[company_id]["company_context"])

    # ------------------------------------------------------------------
    # Topic tracking
    # ------------------------------------------------------------------

    def record_topic(self, company_id: str, domains: List[str]) -> None:
        """Increment topic counters for the given domains."""
        with self._lock:
            self._ensure_company(company_id)
            for domain in domains:
                self._store[company_id]["topic_counts"][domain] += 1

    def get_frequent_topics(self, company_id: str, top_n: int = 5) -> List[Dict[str, Any]]:
        """Return the most frequently asked domains for a company.

        Returns:
            List of {"domain": str, "count": int} sorted by count desc.
        """
        with self._lock:
            self._ensure_company(company_id)
            counter = self._store[company_id]["topic_counts"]
            return [{"domain": d, "count": c} for d, c in counter.most_common(top_n)]

    # ------------------------------------------------------------------
    # Advisory history
    # ------------------------------------------------------------------

    def record_advisory(
        self,
        company_id: str,
        query_summary: str,
        domains: List[str],
        risk_tier: str,
    ) -> None:
        """Store a condensed advisory record."""
        with self._lock:
            self._ensure_company(company_id)
            record = {
                "query_summary": query_summary,
                "domains": domains,
                "risk_tier": risk_tier,
                "timestamp": datetime.utcnow().isoformat(),
            }
            self._store[company_id]["advisory_history"].append(record)

    def get_advisory_history(self, company_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Return the most recent advisory records."""
        with self._lock:
            self._ensure_company(company_id)
            history = self._store[company_id]["advisory_history"]
            return list(reversed(history[-limit:]))

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _ensure_company(self, company_id: str) -> None:
        """Lazily initialise the storage bucket for a company."""
        if company_id not in self._store:
            self._store[company_id] = {
                "company_context": {},
                "topic_counts": Counter(),
                "advisory_history": [],
            }

    def clear(self, company_id: Optional[str] = None) -> None:
        """Clear memory for one company or all companies."""
        with self._lock:
            if company_id:
                self._store.pop(company_id, None)
            else:
                self._store.clear()
