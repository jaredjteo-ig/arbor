"""Knowledge base retrieval for specialist dispatch.

Fetches relevant provisions from the KB before each specialist is called,
ensuring all advisory responses are grounded in actual regulatory content
rather than LLM training data alone.

This module is the bridge between the KB (DataFlow) and the agent pipeline
(Kaizen). It translates between internal domain keys (e.g. "employment_act")
and KB domain names (e.g. "Employment Act"), retrieves matching provisions,
and formats them for injection into specialist prompts.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain key -> KB domain name mapping
# ---------------------------------------------------------------------------

DOMAIN_KEY_TO_KB_NAME: dict[str, str] = {
    "employment_act": "Employment Act",
    "cpf": "CPF",
    "foreign_manpower": "Foreign Manpower",
    "fair_employment": "Fair Employment",
    "wsh": "Workplace Safety and Health",
    "tax": "Tax",
    "pdpa": "PDPA",
    "compliance": "Compliance",
    "general": "General",
}

# Reverse map for convenience
KB_NAME_TO_DOMAIN_KEY: dict[str, str] = {v: k for k, v in DOMAIN_KEY_TO_KB_NAME.items()}


def retrieve_provisions_for_specialist(
    query: str,
    domain: str,
    top_k: int = 10,
) -> list[dict]:
    """Retrieve KB provisions relevant to the query within a specialist's domain.

    Uses the keyword search in ``search_provisions()`` to find provisions whose
    title, section, formal_text, or plain_summary match the query text, filtered
    to the specialist's regulatory domain.

    Args:
        query: The user's query text.
        domain: The specialist's internal domain key (e.g. ``"employment_act"``).
        top_k: Maximum provisions to retrieve.

    Returns:
        List of provision dicts with id, title, section, formal_text,
        plain_summary, authority_level, etc.  Empty list on failure.
    """
    from hr_advisory.kb.admin import search_provisions

    kb_domain_name = DOMAIN_KEY_TO_KB_NAME.get(domain)

    try:
        provisions = search_provisions(
            query=query,
            domain=kb_domain_name,
            limit=top_k,
        )
        logger.info(
            "KB retrieval for domain '%s' (kb_name='%s'): %d provisions found",
            domain,
            kb_domain_name,
            len(provisions),
        )
        return provisions
    except Exception as exc:
        # Log but don't block advisory -- specialists can still advise with
        # lower confidence when the KB is unavailable.
        logger.warning(
            "KB retrieval failed for domain '%s': %s",
            domain,
            exc,
        )
        return []


def format_provisions_for_prompt(provisions: list[dict]) -> str:
    """Format retrieved provisions into a string suitable for agent prompts.

    Produces a numbered list with section references, authority levels,
    plain-language summaries, and (truncated) formal text.  This string is
    intended to be injected into the ``relevant_provisions`` input field of
    specialist agents so they cite real regulatory content.

    Args:
        provisions: List of provision dicts from ``search_provisions()``.

    Returns:
        Formatted string.  Returns a "no provisions found" notice when the
        list is empty so the specialist knows the KB returned nothing.
    """
    if not provisions:
        return "No relevant provisions found in the knowledge base for this query."

    parts: list[str] = []
    for i, prov in enumerate(provisions, 1):
        title = prov.get("title", "Unknown")
        section = prov.get("section", "")
        formal_text = prov.get("formal_text", "")
        plain_summary = prov.get("plain_summary", "")
        authority_level = prov.get("authority_level", "")
        prov_id = prov.get("id", "")

        entry = f"[{i}] {title}"
        if section:
            entry += f" (Section {section})"
        if authority_level:
            entry += f" [{authority_level}]"
        if prov_id:
            entry += f" (id={prov_id})"
        entry += "\n"

        if plain_summary:
            entry += f"Summary: {plain_summary}\n"

        if formal_text:
            # Truncate very long formal text to keep prompt size manageable
            text = formal_text[:500] + "..." if len(formal_text) > 500 else formal_text
            entry += f"Text: {text}\n"

        parts.append(entry)

    return "RELEVANT PROVISIONS FROM KNOWLEDGE BASE:\n\n" + "\n".join(parts)


def provisions_to_dicts(provisions: list[dict]) -> list[dict]:
    """Convert raw KB provision records into the dict format expected by
    ``BaseDomainSpecialist.advise(relevant_provisions=...)``.

    The specialist's ``advise()`` method serialises ``relevant_provisions``
    to JSON and passes it to the LLM as a prompt input.  This function
    ensures each dict has the keys the specialist signatures expect:
    ``id``, ``section``, ``title``, ``formal_text``, ``plain_summary``,
    and ``authority_level``.

    Args:
        provisions: Raw provision dicts from ``search_provisions()``.

    Returns:
        List of cleaned dicts safe for JSON serialisation.
    """
    cleaned: list[dict] = []
    for prov in provisions:
        cleaned.append(
            {
                "id": prov.get("id"),
                "section": prov.get("section", ""),
                "title": prov.get("title", ""),
                "formal_text": prov.get("formal_text", ""),
                "plain_summary": prov.get("plain_summary", ""),
                "authority_level": prov.get("authority_level", ""),
            }
        )
    return cleaned
