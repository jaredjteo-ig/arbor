"""Search endpoints for the knowledge base.

Provides semantic search (via keyword fallback with relevance scoring) and
full-text search with domain, applicability, and date filtering.

Semantic search uses keyword-based relevance scoring as a fallback until
pgvector is configured. Full-text search delegates to search_provisions()
with additional Python-side filtering for act_id and authority_level.
"""

import logging
import time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.kb.admin import search_provisions
from hr_advisory.security.validation import sanitise_input, validate_query_length

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Cached lookups (TTL-based, shared across requests)
# ---------------------------------------------------------------------------

_act_cache: dict[int, str] = {}
_domain_cache: dict[int, str] = {}
_cache_ts: float = 0.0
_CACHE_TTL_SECS = 300  # 5 minutes


def _extract_records(result) -> list[dict]:
    """Extract the record list from a DataFlow ListNode result."""
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


def _refresh_lookups_if_stale() -> None:
    """Refresh act and domain lookup caches if TTL has expired."""
    global _act_cache, _domain_cache, _cache_ts
    now = time.monotonic()
    if _act_cache and (now - _cache_ts) < _CACHE_TTL_SECS:
        return
    try:
        runtime = LocalRuntime()
        wf = WorkflowBuilder()
        wf.add_node(
            "ActListNode", "all_acts", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        wf.add_node(
            "DomainListNode", "all_domains", {"filter": {}, "enable_cache": False, "limit": 10000}
        )
        results, _ = runtime.execute(wf.build())
        acts = _extract_records(results["all_acts"])
        domains = _extract_records(results["all_domains"])
        _act_cache = {
            act["id"]: act.get("title") or act.get("short_name", "Unknown") for act in acts
        }
        _domain_cache = {domain["id"]: domain.get("name", "Unknown") for domain in domains}
        _cache_ts = now
    except Exception as exc:
        logger.warning("Failed to refresh lookups: %s", exc)


def _load_act_lookup() -> dict[int, str]:
    """Return cached act_id -> act title mapping (refreshes every 5 min)."""
    _refresh_lookups_if_stale()
    return _act_cache


def _load_domain_lookup() -> dict[int, str]:
    """Return cached domain_id -> domain name mapping (refreshes every 5 min)."""
    _refresh_lookups_if_stale()
    return _domain_cache


def _calculate_relevance_score(query: str, provision: dict) -> float:
    """Calculate a keyword-density relevance score for a provision.

    Scoring rules (checked in priority order):
    - Query appears in title: 0.95
    - Query appears in plain_summary: 0.85
    - Query appears in formal_text: 0.75
    - No match in any prioritised field: 0.50 (base score -- the provision
      was already returned by search_provisions, so it matched somewhere)

    Args:
        query: The search query string.
        provision: A provision dict with title, plain_summary, formal_text.

    Returns:
        A float between 0.0 and 1.0 representing relevance.
    """
    query_lower = query.lower()

    title = str(provision.get("title", "")).lower()
    if query_lower in title:
        return 0.95

    plain_summary = str(provision.get("plain_summary", "")).lower()
    if query_lower in plain_summary:
        return 0.85

    formal_text = str(provision.get("formal_text", "")).lower()
    if query_lower in formal_text:
        return 0.75

    return 0.50


def _format_semantic_result(
    provision: dict,
    query: str,
    act_lookup: dict[int, str],
    domain_lookup: dict[int, str],
) -> dict:
    """Format a provision into a semantic search result.

    Args:
        provision: A provision dict from search_provisions().
        query: The original search query (for scoring).
        act_lookup: Mapping of act_id -> act display name.
        domain_lookup: Mapping of domain_id -> domain display name.

    Returns:
        A dict with provision_id, title, plain_summary, similarity_score,
        source_act, and domain.
    """
    source_act_id = provision.get("source_act_id")
    domain_id = provision.get("domain_id")

    return {
        "provision_id": provision.get("id"),
        "title": provision.get("title", ""),
        "plain_summary": provision.get("plain_summary", ""),
        "similarity_score": _calculate_relevance_score(query, provision),
        "source_act": act_lookup.get(source_act_id, "Unknown") if source_act_id else "Unknown",
        "domain": domain_lookup.get(domain_id, "Unknown") if domain_id else "Unknown",
    }


def _execute_semantic_search(
    query: str,
    top_k: int,
    domain_id: Optional[int],
    threshold: float,
) -> dict:
    """Execute the semantic search logic and return a structured response.

    Separated from the endpoint handler to enable unit testing without
    FastAPI request/response machinery.

    Args:
        query: Natural-language search query.
        top_k: Maximum number of results to return.
        domain_id: Optional domain ID filter.
        threshold: Minimum similarity score to include a result.

    Returns:
        Dict with query, results, total, top_k, threshold, and domain_filter.
    """
    if not query or not query.strip():
        return {
            "query": query,
            "results": [],
            "total": 0,
            "top_k": top_k,
            "threshold": threshold,
            "domain_filter": domain_id,
        }

    try:
        provisions = search_provisions(query=query, limit=top_k)
    except Exception as exc:
        logger.error(
            "Semantic search failed for query '%s': %s",
            query,
            exc,
        )
        return {
            "query": query,
            "results": [],
            "total": 0,
            "top_k": top_k,
            "threshold": threshold,
            "domain_filter": domain_id,
        }

    act_lookup = _load_act_lookup()
    domain_lookup = _load_domain_lookup()

    formatted = [
        _format_semantic_result(prov, query, act_lookup, domain_lookup) for prov in provisions
    ]

    # Filter by threshold
    filtered = [r for r in formatted if r["similarity_score"] >= threshold]

    # Sort by score descending
    filtered.sort(key=lambda r: r["similarity_score"], reverse=True)

    return {
        "query": query,
        "results": filtered,
        "total": len(filtered),
        "top_k": top_k,
        "threshold": threshold,
        "domain_filter": domain_id,
    }


def _format_fulltext_result(
    provision: dict,
    act_lookup: dict[int, str],
    domain_lookup: dict[int, str],
) -> dict:
    """Format a provision into a full-text search result.

    Returns the provision data with resolved act and domain names.
    """
    source_act_id = provision.get("source_act_id")
    domain_id = provision.get("domain_id")

    return {
        "provision_id": provision.get("id"),
        "title": provision.get("title", ""),
        "section": provision.get("section", ""),
        "plain_summary": provision.get("plain_summary", ""),
        "formal_text": provision.get("formal_text", ""),
        "authority_level": provision.get("authority_level", ""),
        "source_act_id": source_act_id,
        "source_act": act_lookup.get(source_act_id, "Unknown") if source_act_id else "Unknown",
        "domain_id": domain_id,
        "domain": domain_lookup.get(domain_id, "Unknown") if domain_id else "Unknown",
    }


def _resolve_domain_name(domain_id: int, domain_lookup: dict[int, str]) -> Optional[str]:
    """Resolve a domain ID to its name for passing to search_provisions.

    Returns None if the domain ID is not found.
    """
    return domain_lookup.get(domain_id)


def _execute_fulltext_search(
    query: str,
    domain_id: Optional[int],
    act_id: Optional[int],
    authority_level: Optional[str],
    effective_after: Optional[str],
    effective_before: Optional[str],
    page: int,
    page_size: int,
) -> dict:
    """Execute the full-text search logic and return a structured response.

    Separated from the endpoint handler to enable unit testing.

    Args:
        query: Search query string.
        domain_id: Optional domain ID filter (passed to search_provisions).
        act_id: Optional act ID filter (applied in Python after retrieval).
        authority_level: Optional authority level filter (applied in Python).
        effective_after: Optional date filter (for future use).
        effective_before: Optional date filter (for future use).
        page: Page number (1-based).
        page_size: Number of results per page.

    Returns:
        Dict with query, filters, results, total, page, and page_size.
    """
    filters_echo = {
        "domain_id": domain_id,
        "act_id": act_id,
        "authority_level": authority_level,
        "effective_after": effective_after,
        "effective_before": effective_before,
    }

    if not query or not query.strip():
        return {
            "query": query,
            "filters": filters_echo,
            "results": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }

    # Resolve domain name if domain_id is provided, for passing to search_provisions
    domain_name = None
    if domain_id is not None:
        domain_lookup = _load_domain_lookup()
        domain_name = _resolve_domain_name(domain_id, domain_lookup)
        if domain_name is None:
            logger.warning(
                "Domain ID %s not found in lookup, searching without domain filter",
                domain_id,
            )

    # Fetch a generous number of results to allow for post-filtering and pagination.
    # We request more than page_size since we may filter some out in Python.
    fetch_limit = max(page_size * 3, 100)

    try:
        provisions = search_provisions(
            query=query,
            domain=domain_name,
            limit=fetch_limit,
        )
    except Exception as exc:
        logger.error(
            "Full-text search failed for query '%s': %s",
            query,
            exc,
        )
        return {
            "query": query,
            "filters": filters_echo,
            "results": [],
            "total": 0,
            "page": page,
            "page_size": page_size,
        }

    # Post-retrieval filtering
    filtered = provisions

    if act_id is not None:
        filtered = [p for p in filtered if p.get("source_act_id") == act_id]

    if authority_level is not None:
        filtered = [p for p in filtered if p.get("authority_level") == authority_level]

    # Load lookups for formatting
    act_lookup = _load_act_lookup()
    domain_lookup_for_format = _load_domain_lookup()

    total = len(filtered)

    # Pagination (1-based page numbers)
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_results = filtered[start_idx:end_idx]

    formatted = [
        _format_fulltext_result(prov, act_lookup, domain_lookup_for_format) for prov in page_results
    ]

    return {
        "query": query,
        "filters": filters_echo,
        "results": formatted,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


# ---------------------------------------------------------------------------
# FastAPI endpoint handlers
# ---------------------------------------------------------------------------


@router.post("/semantic")
async def semantic_search(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Perform semantic search against knowledge base provisions.

    Uses keyword-based relevance scoring as a fallback for pgvector
    semantic search. Finds provisions by keyword match and ranks them
    by where the match occurs (title > summary > formal text).
    """
    body = await request.json()
    query = sanitise_input(body.get("query", ""))
    top_k = min(body.get("top_k", 10), 100)
    domain_id = body.get("domain_id")
    threshold = body.get("threshold", 0.7)

    is_valid, error_msg = validate_query_length(query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    return _execute_semantic_search(
        query=query,
        top_k=top_k,
        domain_id=domain_id,
        threshold=threshold,
    )


@router.post("/fulltext")
async def fulltext_search(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Perform full-text search with domain and date filters.

    Searches provision formal text and plain summaries using keyword
    matching via search_provisions(), with optional post-retrieval
    filters for act_id and authority_level. Supports pagination.
    """
    body = await request.json()
    query = sanitise_input(body.get("query", ""))
    domain_id = body.get("domain_id")
    act_id = body.get("act_id")
    authority_level = body.get("authority_level")
    effective_after = body.get("effective_after")
    effective_before = body.get("effective_before")
    page = body.get("page", 1)
    page_size = min(body.get("page_size", 20), 100)

    is_valid, error_msg = validate_query_length(query)
    if not is_valid:
        raise HTTPException(status_code=400, detail=error_msg)

    return _execute_fulltext_search(
        query=query,
        domain_id=domain_id,
        act_id=act_id,
        authority_level=authority_level,
        effective_after=effective_after,
        effective_before=effective_before,
        page=page,
        page_size=page_size,
    )
