"""CLI-style administration functions for the knowledge base.

High-level convenience functions for adding, updating, querying, and
reporting on KB content. All database operations use DataFlow workflow
nodes through the KBContentPipeline.
"""

import logging
from datetime import datetime
from typing import Optional

from kailash.runtime import LocalRuntime
from kailash.workflow.builder import WorkflowBuilder

logger = logging.getLogger(__name__)


def _execute(node_type: str, node_id: str, params: dict) -> dict:
    """Run a single-node workflow and return the node result."""
    runtime = LocalRuntime()
    wf = WorkflowBuilder()
    wf.add_node(node_type, node_id, params)
    results, _ = runtime.execute(wf.build())
    return results[node_id]


def _extract_records(result) -> list[dict]:
    """Extract the record list from a ListNode result.

    DataFlow ListNode returns either a plain list or
    ``{"records": [...], "count": N, ...}``.
    """
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


def add_provision(act_short_name: str, provision_data: dict) -> dict:
    """Add a single provision to the KB.

    Resolves the act by short_name and delegates to KBContentPipeline.

    Args:
        act_short_name: The short name of the act this provision belongs to.
        provision_data: Dict with section, title, formal_text, authority_level,
            domain_name, and optionally other Provision fields.

    Returns:
        The created provision as a dict (including ``id``).

    Raises:
        ValueError: If the act or domain is not found.
    """
    from hr_advisory.kb.pipeline import KBContentPipeline

    pipeline = KBContentPipeline()
    data = dict(provision_data)
    data["act_short_name"] = act_short_name

    logger.info("Adding provision '%s' to act '%s'", data.get("section"), act_short_name)
    return pipeline.load_provision(data)


def update_provision(provision_id: int, updates: dict, reason: str) -> dict:
    """Update a provision by creating a new version.

    The old provision is marked as superseded (is_active=False,
    superseded_by_id=new_id) and a new provision record is created
    with the updated fields.

    Args:
        provision_id: The ID of the provision to update.
        updates: Dict of field -> new_value to apply.
        reason: Human-readable reason for the update (for audit).

    Returns:
        The newly created provision as a dict (including ``id``).

    Raises:
        ValueError: If the original provision is not found.
    """
    runtime = LocalRuntime()

    # Read original provision
    wf_read = WorkflowBuilder()
    wf_read.add_node("ProvisionReadNode", "read", {"id": provision_id})
    results, _ = runtime.execute(wf_read.build())
    original = results["read"]

    if not original:
        raise ValueError(f"Provision with id={provision_id} not found. Cannot update.")

    # Build data for the new version: start from original, apply updates
    new_data = dict(original)
    # Remove fields that should not be copied to the new version
    for key in (
        "id",
        "created_at",
        "updated_at",
        "deleted_at",
        "superseded_date",
        "superseded_by_id",
    ):
        new_data.pop(key, None)

    # Apply updates
    new_data.update(updates)
    new_data["is_active"] = True

    # Convert datetime strings if needed
    for date_field in ("effective_date", "superseded_date"):
        val = new_data.get(date_field)
        if isinstance(val, str):
            new_data[date_field] = datetime.fromisoformat(val)

    # Create new version
    wf_create = WorkflowBuilder()
    wf_create.add_node("ProvisionCreateNode", "create_new", new_data)
    create_results, _ = runtime.execute(wf_create.build())
    new_provision = create_results["create_new"]

    logger.info(
        "Created new provision version id=%s (supersedes id=%s, reason: %s)",
        new_provision["id"],
        provision_id,
        reason,
    )

    # Mark old version as superseded
    wf_update = WorkflowBuilder()
    wf_update.add_node(
        "ProvisionUpdateNode",
        "supersede",
        {
            "filter": {"id": provision_id},
            "fields": {
                "is_active": False,
                "superseded_by_id": new_provision["id"],
                "superseded_date": datetime.now(tz=None),
            },
        },
    )
    runtime.execute(wf_update.build())

    logger.info("Marked provision id=%s as superseded", provision_id)
    return new_provision


def get_kb_stats() -> dict:
    """Get knowledge base statistics.

    Returns a dict with counts of all entity types:
    acts, domains, provisions, applicability_rules, practical_examples,
    cross_references, rate_tables.
    """
    runtime = LocalRuntime()
    stats = {}

    entity_nodes = {
        "acts": "ActListNode",
        "domains": "DomainListNode",
        "provisions": "ProvisionListNode",
        "applicability_rules": "ApplicabilityRuleListNode",
        "practical_examples": "PracticalExampleListNode",
        "cross_references": "CrossReferenceListNode",
        "rate_tables": "RateTableListNode",
    }

    for entity_name, node_type in entity_nodes.items():
        try:
            wf = WorkflowBuilder()
            wf.add_node(
                node_type,
                f"count_{entity_name}",
                {"filter": {}, "enable_cache": False, "limit": 10000},
            )
            results, _ = runtime.execute(wf.build())
            data = results[f"count_{entity_name}"]
            records = _extract_records(data)
            stats[entity_name] = len(records)
        except Exception as exc:
            logger.error("Failed to count %s: %s", entity_name, exc)
            stats[entity_name] = 0

    logger.info("KB stats: %s", stats)
    return stats


def search_provisions(
    query: str,
    domain: Optional[str] = None,
    limit: int = 10,
) -> list:
    """Search provisions by keyword in title, section, and formal_text.

    Uses DataFlow ListNode with filter to find matching provisions.
    For full semantic search, use the EmbeddingPipeline with pgvector.

    Args:
        query: Search query string.
        domain: Optional domain name to filter by.
        limit: Maximum number of results to return.

    Returns:
        List of matching provision dicts.
    """
    runtime = LocalRuntime()

    # Get all provisions (DataFlow ListNode doesn't support LIKE/ILIKE natively,
    # so we filter in Python)
    wf = WorkflowBuilder()
    wf.add_node(
        "ProvisionListNode", "all_provs", {"filter": {}, "enable_cache": False, "limit": 10000}
    )
    results, _ = runtime.execute(wf.build())
    all_provisions = _extract_records(results["all_provs"])

    if not all_provisions:
        return []

    # If domain filter is specified, resolve domain_id first
    domain_id = None
    if domain:
        wf_domain = WorkflowBuilder()
        wf_domain.add_node(
            "DomainListNode", "find_domain", {"filter": {"name": domain}, "enable_cache": False}
        )
        domain_results, _ = runtime.execute(wf_domain.build())
        domains = _extract_records(domain_results["find_domain"])
        if domains:
            domain_id = domains[0]["id"]
        else:
            logger.warning("Domain '%s' not found, returning empty results", domain)
            return []

    # Filter provisions using word-level relevance scoring
    query_lower = query.lower().strip()

    # Extract meaningful keywords (skip stop words and very short tokens)
    _stop = frozenset(
        {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "could",
            "should",
            "may",
            "might",
            "shall",
            "can",
            "need",
            "must",
            "i",
            "me",
            "my",
            "we",
            "our",
            "you",
            "your",
            "he",
            "she",
            "it",
            "they",
            "them",
            "their",
            "this",
            "that",
            "what",
            "which",
            "who",
            "how",
            "when",
            "where",
            "why",
            "if",
            "of",
            "in",
            "on",
            "at",
            "to",
            "for",
            "with",
            "by",
            "from",
            "about",
            "not",
            "no",
            "or",
            "and",
            "but",
            "so",
            "as",
            "than",
        }
    )
    query_words = [w for w in query_lower.split() if len(w) > 2 and w not in _stop]

    matched = []
    scored: list[tuple[int, dict]] = []
    for prov in all_provisions:
        # Domain filter
        if domain_id is not None and prov.get("domain_id") != domain_id:
            continue

        # If no meaningful query words, return all provisions for this domain
        if not query_words:
            matched.append(prov)
            if len(matched) >= limit:
                break
        else:
            # Score by keyword overlap — count how many query words appear
            searchable = " ".join(
                str(prov.get(field, ""))
                for field in ("title", "section", "formal_text", "plain_summary")
            ).lower()

            score = sum(1 for w in query_words if w in searchable)
            if score > 0:
                scored.append((score, prov))

    # If we used scoring, sort by relevance (most keyword matches first)
    if scored:
        scored.sort(key=lambda x: x[0], reverse=True)
        matched = [prov for _, prov in scored[:limit]]

    logger.info("Search for '%s' returned %d results", query, len(matched))
    return matched
