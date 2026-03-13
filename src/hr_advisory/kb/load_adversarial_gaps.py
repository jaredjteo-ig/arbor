"""Loader for adversarial scenario gap provisions (T082).

Inserts the provisions defined in ``kb.content.adversarial_gaps`` into
the knowledge base via the ``KBContentPipeline``.

Usage::

    from hr_advisory.kb.pipeline import KBContentPipeline
    from hr_advisory.kb.load_adversarial_gaps import load_gaps

    pipeline = KBContentPipeline()
    summary = load_gaps(pipeline)
    print(f"Loaded {len(summary['provisions'])} provisions")
"""

import logging

from hr_advisory.kb.content.adversarial_gaps import get_provisions

logger = logging.getLogger(__name__)

# Acts referenced by the gap provisions.  The loader ensures each
# exists before inserting provisions that reference it.
_REFERENCED_ACTS: list[dict] = [
    {
        "title": "Employment Act 1968",
        "short_name": "EA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/EmplA1968",
        "is_active": True,
    },
    {
        "title": "Child Development Co-Savings Act",
        "short_name": "CDCSA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Social and Family Development",
        "official_url": "https://sso.agc.gov.sg/Act/CDCSA2001",
        "is_active": True,
    },
    {
        "title": "Central Provident Fund Act",
        "short_name": "CPFA",
        "authority_type": "statute",
        "issuing_body": "Central Provident Fund Board",
        "official_url": "https://sso.agc.gov.sg/Act/CPFA1953",
        "is_active": True,
    },
    {
        "title": "Platform Workers Act 2024",
        "short_name": "PWA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/PWA2024",
        "is_active": True,
    },
    {
        "title": "Personal Data Protection Act",
        "short_name": "PDPA",
        "authority_type": "statute",
        "issuing_body": "Personal Data Protection Commission",
        "official_url": "https://sso.agc.gov.sg/Act/PDPA2012",
        "is_active": True,
    },
    {
        "title": "Workplace Safety and Health Act",
        "short_name": "WSHA",
        "authority_type": "statute",
        "issuing_body": "Ministry of Manpower",
        "official_url": "https://sso.agc.gov.sg/Act/WSHA2006",
        "is_active": True,
    },
    {
        "title": "Tripartite Guidelines on Fair Employment Practices",
        "short_name": "TGFEP",
        "authority_type": "tripartite_guideline",
        "issuing_body": "Tripartite Alliance for Fair and Progressive Employment Practices",
        "official_url": "https://www.tal.sg/tafep/getting-started/fair/tripartite-guidelines",
        "is_active": True,
    },
]

# Domains introduced by the adversarial gaps that may not already
# exist in the KB.
_NEW_DOMAINS: list[dict] = [
    {
        "name": "Platform Workers",
        "description": (
            "Platform Workers Act 2024 provisions covering CPF "
            "contributions, work injury compensation, and housing/retirement "
            "adequacy for gig economy workers."
        ),
        "sort_order": 20,
    },
    {
        "name": "Part-Time Employment",
        "description": (
            "Part-time employee regulations under the Employment Act and "
            "Tripartite Guidelines, including pro-rated leave, overtime, "
            "and public holiday entitlements."
        ),
        "sort_order": 21,
    },
]


def load_gaps(pipeline) -> dict:
    """Insert all adversarial-gap provisions into the KB.

    Args:
        pipeline: A ``KBContentPipeline`` instance (or compatible object
            with ``load_act``, ``load_domain``, and ``load_provision``
            methods).

    Returns:
        A summary dict with keys ``acts``, ``domains``, ``provisions``,
        each containing the loaded records.
    """
    summary: dict = {
        "acts": [],
        "domains": [],
        "provisions": [],
    }

    # 1. Ensure all referenced acts exist
    for act_data in _REFERENCED_ACTS:
        act = pipeline.load_act(act_data)
        summary["acts"].append(act)
        logger.info("Ensured act: %s (id=%s)", act_data["short_name"], act.get("id"))

    # 2. Ensure new domains exist
    for domain_data in _NEW_DOMAINS:
        domain = pipeline.load_domain(domain_data)
        summary["domains"].append(domain)
        logger.info("Ensured domain: %s (id=%s)", domain_data["name"], domain.get("id"))

    # 3. Load all provisions
    provisions = get_provisions()
    for prov_data in provisions:
        provision = pipeline.load_provision(prov_data)
        summary["provisions"].append(provision)
        logger.info(
            "Loaded provision: %s - %s",
            prov_data["section"],
            prov_data["title"],
        )

    logger.info(
        "Adversarial gap loading complete: %d acts, %d domains, %d provisions",
        len(summary["acts"]),
        len(summary["domains"]),
        len(summary["provisions"]),
    )
    return summary
