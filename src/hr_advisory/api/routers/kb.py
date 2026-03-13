"""Knowledge base query endpoints.

Handles queries to the regulatory knowledge base including
provisions, acts, domains, and cross-references.
All database operations use DataFlow workflow nodes via Kailash runtime.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.security.validation import sanitise_input, validate_query_length

logger = logging.getLogger(__name__)

router = APIRouter()


def _execute_node(node_type: str, node_id: str, params: dict) -> dict:
    """Run a single DataFlow workflow node and return the result."""
    from kailash.runtime import LocalRuntime
    from kailash.workflow.builder import WorkflowBuilder

    wf = WorkflowBuilder()
    wf.add_node(node_type, node_id, params)
    runtime = LocalRuntime()
    results, _ = runtime.execute(wf.build())
    return results[node_id]


def _extract_records(result) -> list[dict]:
    """Extract the record list from a DataFlow ListNode result.

    DataFlow ListNode returns either a plain list or
    ``{"records": [...], "count": N, ...}``.
    """
    if isinstance(result, list):
        return result
    if isinstance(result, dict) and "records" in result:
        return result["records"]
    return []


@router.get("/acts")
async def list_acts(current_user: dict = Depends(get_current_user)) -> dict:
    """List all legislative acts in the knowledge base."""
    try:
        result = _execute_node(
            "ActListNode",
            "list_acts",
            {"filter": {}, "enable_cache": False, "limit": 1000},
        )
    except Exception as exc:
        logger.error("Failed to query acts from knowledge base: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve acts. Please try again later.",
        ) from exc

    records = _extract_records(result)
    return {
        "acts": records,
        "total": len(records),
    }


@router.get("/domains")
async def list_domains(current_user: dict = Depends(get_current_user)) -> dict:
    """List all HR knowledge domains."""
    try:
        result = _execute_node(
            "DomainListNode",
            "list_domains",
            {"filter": {}, "enable_cache": False, "limit": 1000},
        )
    except Exception as exc:
        logger.error("Failed to query domains from knowledge base: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve domains. Please try again later.",
        ) from exc

    records = _extract_records(result)
    return {
        "domains": records,
        "total": len(records),
    }


@router.get("/provisions/ref/{reference}")
async def get_provision_by_reference(
    reference: str,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Look up a provision by its string reference (e.g. 'EA-S10-notice').

    Searches the provision section and title fields for a match against
    the given reference string. Returns the first matching provision
    with cross-references, applicability rules, and practical examples.
    """
    # Search all provisions for one whose section matches the reference
    try:
        result = _execute_node(
            "ProvisionListNode",
            "lookup_by_ref",
            {"filter": {}, "enable_cache": False, "limit": 5000},
        )
    except Exception as exc:
        logger.error("Failed to query provisions for reference lookup: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to search provisions. Please try again later.",
        ) from exc

    records = _extract_records(result)

    # Try exact match on section first, then partial match
    ref_lower = reference.lower()
    match = None
    for prov in records:
        section = str(prov.get("section", "")).lower()
        if section == ref_lower:
            match = prov
            break

    if match is None:
        # Try partial match on section or title
        for prov in records:
            section = str(prov.get("section", "")).lower()
            title = str(prov.get("title", "")).lower()
            if ref_lower in section or ref_lower in title:
                match = prov
                break

    if match is None:
        raise HTTPException(
            status_code=404,
            detail=f"Provision with reference '{reference}' not found",
        )

    provision_id = match["id"]

    # Fetch related data
    cross_references: list[dict] = []
    applicability_rules: list[dict] = []
    practical_examples: list[dict] = []

    try:
        xref_result = _execute_node(
            "CrossReferenceListNode",
            "list_xrefs_ref",
            {
                "filter": {"source_provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        cross_references = _extract_records(xref_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch cross-references for provision ref=%s: %s",
            reference,
            exc,
        )

    try:
        rules_result = _execute_node(
            "ApplicabilityRuleListNode",
            "list_rules_ref",
            {
                "filter": {"provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        applicability_rules = _extract_records(rules_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch applicability rules for provision ref=%s: %s",
            reference,
            exc,
        )

    try:
        examples_result = _execute_node(
            "PracticalExampleListNode",
            "list_examples_ref",
            {
                "filter": {"provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        practical_examples = _extract_records(examples_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch practical examples for provision ref=%s: %s",
            reference,
            exc,
        )

    match["cross_references"] = cross_references
    match["applicability_rules"] = applicability_rules
    match["practical_examples"] = practical_examples

    return match


@router.get("/provisions/{provision_id}")
async def get_provision(
    provision_id: int,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Get a specific provision by ID with related cross-references."""
    # Read the provision
    try:
        provision = _execute_node(
            "ProvisionReadNode",
            "read_provision",
            {"conditions": {"id": provision_id}},
        )
    except Exception as exc:
        logger.error("Failed to read provision id=%s: %s", provision_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve provision. Please try again later.",
        ) from exc

    if not provision or provision.get("error") or provision.get("failed"):
        raise HTTPException(
            status_code=404,
            detail=f"Provision with id={provision_id} not found",
        )

    # Fetch related data: cross-references, applicability rules, practical examples
    cross_references: list[dict] = []
    applicability_rules: list[dict] = []
    practical_examples: list[dict] = []

    try:
        xref_result = _execute_node(
            "CrossReferenceListNode",
            "list_xrefs",
            {
                "filter": {"source_provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        cross_references = _extract_records(xref_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch cross-references for provision id=%s: %s",
            provision_id,
            exc,
        )

    try:
        rules_result = _execute_node(
            "ApplicabilityRuleListNode",
            "list_rules",
            {
                "filter": {"provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        applicability_rules = _extract_records(rules_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch applicability rules for provision id=%s: %s",
            provision_id,
            exc,
        )

    try:
        examples_result = _execute_node(
            "PracticalExampleListNode",
            "list_examples",
            {
                "filter": {"provision_id": provision_id},
                "enable_cache": False,
                "limit": 1000,
            },
        )
        practical_examples = _extract_records(examples_result)
    except Exception as exc:
        logger.warning(
            "Failed to fetch practical examples for provision id=%s: %s",
            provision_id,
            exc,
        )

    provision["cross_references"] = cross_references
    provision["applicability_rules"] = applicability_rules
    provision["practical_examples"] = practical_examples

    return provision


@router.post("/query")
async def query_provisions(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Query provisions by domain, act, or keyword filters.

    Supports filtering by domain_id, act_id, and keyword.
    When a keyword is provided, uses the search_provisions helper
    for in-memory text matching across title, section, formal_text,
    and plain_summary fields.
    """
    body = await request.json()
    domain_id = body.get("domain_id")
    act_id = body.get("act_id")
    keyword = sanitise_input(body.get("keyword", ""))
    limit = min(body.get("limit", 50), 100)

    if keyword:
        is_valid, error_msg = validate_query_length(keyword)
        if not is_valid:
            raise HTTPException(status_code=400, detail=error_msg)

    # Build the DataFlow filter from the provided criteria
    df_filter: dict = {}
    if domain_id is not None:
        df_filter["domain_id"] = domain_id
    if act_id is not None:
        df_filter["source_act_id"] = act_id

    try:
        result = _execute_node(
            "ProvisionListNode",
            "query_provisions",
            {"filter": df_filter, "enable_cache": False, "limit": limit},
        )
    except Exception as exc:
        logger.error(
            "Failed to query provisions (domain_id=%s, act_id=%s): %s",
            domain_id,
            act_id,
            exc,
        )
        raise HTTPException(
            status_code=500,
            detail="Failed to query provisions. Please try again later.",
        ) from exc

    records = _extract_records(result)

    # Apply keyword filter in Python if specified
    if keyword:
        keyword_lower = keyword.lower()
        filtered = []
        for prov in records:
            searchable = " ".join(
                str(prov.get(field, ""))
                for field in ("title", "section", "formal_text", "plain_summary")
            ).lower()
            if keyword_lower in searchable:
                filtered.append(prov)
        records = filtered

    return {
        "filters": {
            "domain_id": domain_id,
            "act_id": act_id,
            "keyword": keyword,
        },
        "provisions": records,
        "total": len(records),
    }
