"""Canonical mapping from domain keys to KB provisions.

The KB stores Domain rows as sub-areas (e.g. "CPF Contribution Rates",
"CPF Wage Ceilings", "CPF Allocation", "CPF Compliance") rather than
the top-level regulatory domain ("CPF"). Filtering provisions by
`Domain.name == "cpf"` always returns zero.

The right lookup goes through the Act table:
    domain_key → Act.short_name → all Provisions where source_act_id = Act.id

This module centralises that mapping so the advisory engine, the
compliance health check, the shadow agent, and any future consumer
agree on the canonical translation. Previously the mapping lived
inline in `api/routers/compliance.py:91-105`; lifting it here lets the
advisory engine use it without importing a FastAPI router.

Red-team P5-AD-followup (citations side-finding from
workspaces/obayashi/04-validate/13-redteam-comprehensive-2026-05-19.md
post-deploy walk on 2026-05-19): the advisory pre-classifier wired in
P5-RT3-AD called `_kb_search_provisions(domain="cpf")` and got zero
hits — leaving `provisions_cited` empty in the conversation history.
Routing through this module gives the citations array real content.
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)


# Canonical domain keys. These match the values emitted by
# `_extract_domains_from_tools` and consumed by the compliance router
# and shadow agent. Keep these stable — they're the cross-module
# contract.
DOMAIN_KEYS: tuple[str, ...] = (
    "employment_act",
    "cpf",
    "foreign_manpower",
    "wsh",
    "fair_employment",
    "tax",
)


# Some callers (the advisory_domain_classifier, mobile API consumers)
# use legacy alternate spellings. Normalise to the canonical key set.
DOMAIN_ALIASES: dict[str, str] = {
    "efma": "foreign_manpower",
    "tafep": "fair_employment",
    "tax_iras": "tax",
}


def normalize_domain_key(domain_key: str) -> str:
    """Convert any accepted spelling to the canonical key."""
    return DOMAIN_ALIASES.get(domain_key, domain_key)


# domain key → list of Act.short_name values that store provisions for
# that domain. The shared module lifts this from the compliance router
# verbatim so existing behaviour is preserved.
_DOMAIN_TO_ACT_SHORT_NAMES: dict[str, list[str]] = {
    "employment_act": ["EA"],
    "cpf": ["CPFA"],
    "foreign_manpower": ["EFMA"],
    "tax": ["CDCSA"],
    "wsh": ["CDCSA"],
    "fair_employment": ["TGFEP"],
}


# For domains that share an Act (tax + wsh both under CDCSA), narrow
# further by sub-domain name. Empty list = no sub-filter.
_DOMAIN_TO_KB_DOMAIN_NAMES: dict[str, list[str]] = {
    "tax": ["Tax Obligations"],
    "wsh": ["Workplace Safety & Health"],
}


def get_act_short_names(domain_key: str) -> list[str]:
    """Return the Act short_name list for a domain. Empty if unknown."""
    return list(_DOMAIN_TO_ACT_SHORT_NAMES.get(normalize_domain_key(domain_key), []))


def get_kb_subdomain_names(domain_key: str) -> list[str]:
    """Return the sub-domain filter for shared-act domains. Empty list otherwise."""
    return list(_DOMAIN_TO_KB_DOMAIN_NAMES.get(normalize_domain_key(domain_key), []))


def provisions_for_domain(
    domain_key: str,
    limit: int = 100,
    query: Optional[str] = None,
) -> list[dict]:
    """Fetch all provisions for a domain, going through the Act table.

    Args:
        domain_key: canonical domain key (e.g. "cpf"). Aliases like
            "efma", "tafep", "tax_iras" are auto-normalised.
        limit: max rows to return.
        query: optional keyword string. When provided, rows are
            re-ranked by a simple word-overlap score against
            title + section + plain_summary. Empty `query` skips
            ranking (compliance check use-case).

    Returns:
        List of provision dicts (raw DataFlow output). Empty list on
        unknown domain OR when the Act has no provisions yet.
    """
    from hr_advisory.services import dataflow_crud

    key = normalize_domain_key(domain_key)
    act_short_names = get_act_short_names(key)
    if not act_short_names:
        logger.debug(
            "provisions_for_domain: no Act mapping for domain=%r — returning []",
            domain_key,
        )
        return []

    provisions: list[dict] = []
    for short_name in act_short_names:
        acts = dataflow_crud.list_records("Act", {"short_name": short_name})
        if not acts:
            continue
        act_id = acts[0]["id"]
        rows = dataflow_crud.list_records(
            "Provision", {"source_act_id": act_id, "is_active": True}
        )
        provisions.extend(rows)

    # Sub-domain filter for shared-act domains.
    subdomain_names = get_kb_subdomain_names(key)
    if subdomain_names and provisions:
        domain_ids: set[int] = set()
        for dn in subdomain_names:
            for d in dataflow_crud.list_records("Domain", {"name": dn}):
                domain_ids.add(d["id"])
        if domain_ids:
            provisions = [p for p in provisions if p.get("domain_id") in domain_ids]

    # Optional keyword-based ranking for advisory pre-seed use.
    if query:
        q = query.lower().strip()
        if q:
            words = [w for w in q.split() if len(w) >= 3]

            def score(p: dict) -> int:
                hay = " ".join(
                    str(p.get(f) or "")
                    for f in ("title", "section", "plain_summary", "formal_text")
                ).lower()
                return sum(1 for w in words if w in hay)

            provisions.sort(key=score, reverse=True)

    return provisions[:limit]
