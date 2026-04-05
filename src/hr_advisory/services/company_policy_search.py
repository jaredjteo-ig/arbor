# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Company policy search service (T010).

Provides keyword-based search over a company's active policies using
DataFlow nodes. Follows the same scoring pattern as the KB search in
advisory_engine.py (stopword removal, word overlap scoring).
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

__all__ = ["search_company_policies"]

# Stopwords (same set used by advisory_engine._search_python_kb)
_STOP_WORDS: frozenset[str] = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "have", "has",
        "do", "does", "did", "will", "would", "can", "need", "must", "i",
        "me", "my", "we", "you", "your", "he", "she", "it", "they", "this",
        "that", "what", "which", "who", "how", "when", "where", "why", "if",
        "of", "in", "on", "at", "to", "for", "with", "by", "from", "about",
        "not", "no", "or", "and", "but", "so", "as",
    }
)


def _fetch_active_policies(company_id: int, category: str | None = None) -> list[dict]:
    """Fetch active policies for a company from DataFlow.

    Uses CompanyPolicyListNode with filter for company_id, is_active=True,
    and optional category filter.

    Returns:
        List of policy dicts from the database.

    Raises:
        Any exception from the Kailash runtime or DataFlow layer.
    """
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    import hr_advisory.models  # noqa: F401 -- ensure models are registered

    filter_dict: dict[str, Any] = {
        "company_id": company_id,
        "is_active": True,
    }
    if category:
        filter_dict["category"] = category

    wf = WorkflowBuilder()
    wf.add_node(
        "CompanyPolicyListNode",
        "list",
        {"filter": filter_dict, "limit": 10000, "enable_cache": False},
    )
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    raw = results["list"]
    if isinstance(raw, dict) and "records" in raw:
        return raw["records"]
    if isinstance(raw, list):
        return raw
    return []


def search_company_policies(
    query: str,
    company_id: int,
    category: str | None = None,
    limit: int = 5,
) -> list[dict] | dict:
    """Search company policies by keyword relevance.

    Uses the same scoring pattern as _search_python_kb in advisory_engine.py:
    stopword removal, word overlap, ranked by score.

    Args:
        query: Search query string.
        company_id: Company ID to search policies for.
        category: Optional category filter (e.g. 'leave', 'flexible_work').
        limit: Maximum number of results to return.

    Returns:
        List of result dicts with keys: policy_id, title, category,
        content_excerpt, effective_date, version_number, authority_level.
        When no results match but policies exist, returns a structured dict
        with keys: results, total_company_policies, message.
        Returns [] if query is empty or on error.
    """
    if not query or not query.strip():
        return []

    # Tokenize query, remove stopwords
    query_lower = query.lower()
    query_words = [w for w in query_lower.split() if len(w) > 2 and w not in _STOP_WORDS]

    if not query_words:
        return []

    # Fetch active policies from DataFlow
    try:
        all_policies = _fetch_active_policies(company_id, category=None)
    except Exception as exc:
        logger.warning(
            "Failed to fetch company policies for company_id=%d: %s",
            company_id,
            exc,
        )
        return []

    if not all_policies:
        return {
            "results": [],
            "total_company_policies": 0,
            "message": "No company policies found. The company has not uploaded any policies yet.",
        }

    # Apply category filter for scoring
    policies_to_search = all_policies
    if category:
        policies_to_search = [p for p in all_policies if p.get("category") == category]

    if not policies_to_search:
        return {
            "results": [],
            "total_company_policies": len(all_policies),
            "message": (
                f"No company policies matched the category '{category}'. "
                f"The company has {len(all_policies)} policies but none in this category."
            ),
        }

    # Score by keyword overlap (same pattern as _search_python_kb)
    scored: list[tuple[int, dict]] = []
    for policy in policies_to_search:
        searchable = " ".join(
            str(policy.get(f, ""))
            for f in ("title", "category", "policy_type", "content")
        ).lower()
        score = sum(1 for w in query_words if w in searchable)
        if score > 0:
            scored.append((score, policy))

    scored.sort(key=lambda x: x[0], reverse=True)

    if not scored:
        return {
            "results": [],
            "total_company_policies": len(all_policies),
            "message": (
                f"No company policies matched this query. "
                f"The company has {len(all_policies)} policies but none are relevant to this topic."
            ),
        }

    # Build result dicts
    results: list[dict] = []
    for _score, policy in scored[:limit]:
        content = str(policy.get("content", ""))
        content_excerpt = content[:2000] if len(content) > 2000 else content

        results.append(
            {
                "policy_id": policy.get("id", 0),
                "title": policy.get("title", ""),
                "category": policy.get("category", ""),
                "content_excerpt": content_excerpt,
                "effective_date": policy.get("effective_date", ""),
                "version_number": policy.get("version_number", 1),
                "authority_level": "company_policy",
            }
        )

    return results
