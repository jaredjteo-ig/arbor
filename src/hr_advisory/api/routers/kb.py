"""Knowledge base query endpoints.

Handles queries to the regulatory knowledge base including
provisions, acts, domains, and cross-references.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request

from hr_advisory.api.middleware.auth_middleware import get_current_user
from hr_advisory.security.validation import sanitise_input, validate_query_length
from hr_advisory.services import dataflow_crud

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/acts")
async def list_acts(current_user: dict = Depends(get_current_user)) -> dict:
    """List all legislative acts in the knowledge base."""
    try:
        records = dataflow_crud.list_records("Act", {}, limit=1000)
    except Exception as exc:
        logger.error("Failed to query acts from knowledge base: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve acts. Please try again later.",
        ) from exc

    return {
        "acts": records,
        "total": len(records),
    }


@router.get("/domains")
async def list_domains(current_user: dict = Depends(get_current_user)) -> dict:
    """List all HR knowledge domains."""
    try:
        records = dataflow_crud.list_records("Domain", {}, limit=1000)
    except Exception as exc:
        logger.error("Failed to query domains from knowledge base: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve domains. Please try again later.",
        ) from exc

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
        records = dataflow_crud.list_records("Provision", {}, limit=5000)
    except Exception as exc:
        logger.error("Failed to query provisions for reference lookup: %s", exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to search provisions. Please try again later.",
        ) from exc

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
        cross_references = dataflow_crud.list_records(
            "CrossReference", {"source_provision_id": provision_id}, limit=1000
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch cross-references for provision ref=%s: %s",
            reference,
            exc,
        )

    try:
        applicability_rules = dataflow_crud.list_records(
            "ApplicabilityRule", {"provision_id": provision_id}, limit=1000
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch applicability rules for provision ref=%s: %s",
            reference,
            exc,
        )

    try:
        practical_examples = dataflow_crud.list_records(
            "PracticalExample", {"provision_id": provision_id}, limit=1000
        )
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
        provision = dataflow_crud.read("Provision", provision_id)
    except Exception as exc:
        logger.error("Failed to read provision id=%s: %s", provision_id, exc)
        raise HTTPException(
            status_code=500,
            detail="Failed to retrieve provision. Please try again later.",
        ) from exc

    if not provision:
        raise HTTPException(
            status_code=404,
            detail=f"Provision with id={provision_id} not found",
        )

    # Fetch related data: cross-references, applicability rules, practical examples
    cross_references: list[dict] = []
    applicability_rules: list[dict] = []
    practical_examples: list[dict] = []

    try:
        cross_references = dataflow_crud.list_records(
            "CrossReference", {"source_provision_id": provision_id}, limit=1000
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch cross-references for provision id=%s: %s",
            provision_id,
            exc,
        )

    try:
        applicability_rules = dataflow_crud.list_records(
            "ApplicabilityRule", {"provision_id": provision_id}, limit=1000
        )
    except Exception as exc:
        logger.warning(
            "Failed to fetch applicability rules for provision id=%s: %s",
            provision_id,
            exc,
        )

    try:
        practical_examples = dataflow_crud.list_records(
            "PracticalExample", {"provision_id": provision_id}, limit=1000
        )
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
        records = dataflow_crud.list_records("Provision", df_filter, limit=limit)
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
