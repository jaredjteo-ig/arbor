"""Compliance check endpoints.

Evaluates a company's HR practices against Singapore employment
legislation and tripartite guidelines by querying the knowledge base
for provision coverage per regulatory domain.  Identifies gaps and
provides remediation recommendations based on real KB data.
"""

import logging
import time
from collections import OrderedDict
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Request

from hr_advisory.api.middleware.auth_middleware import require_role
from hr_advisory.api.middleware.rate_limit import check_rate_limit
from hr_advisory.api.middleware.tenant_isolation import validate_company_access
from hr_advisory.kb.admin import get_kb_stats
from hr_advisory.kb.admin import search_provisions as _kb_search_provisions

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Compliance status cache (5-minute TTL) ──────────────────────────
_compliance_cache: OrderedDict[int, tuple[float, dict]] = OrderedDict()
_CACHE_TTL = 300  # 5 minutes
_MAX_CACHE_ENTRIES = 100


def _get_cached_compliance(company_id: int) -> dict | None:
    entry = _compliance_cache.get(company_id)
    if entry and (time.time() - entry[0]) < _CACHE_TTL:
        _compliance_cache.move_to_end(company_id)
        return entry[1]
    if entry:
        del _compliance_cache[company_id]
    return None


def _set_cached_compliance(company_id: int, data: dict) -> None:
    while len(_compliance_cache) >= _MAX_CACHE_ENTRIES:
        _compliance_cache.popitem(last=False)
    _compliance_cache[company_id] = (time.time(), data)


def invalidate_compliance_cache(company_id: int) -> None:
    """Call from policies router when policies change."""
    _compliance_cache.pop(company_id, None)


# Domains considered critical for Singapore HR compliance.
# Missing provisions in these domains triggers "non_compliant" status.
CRITICAL_DOMAINS = frozenset({"employment_act", "cpf"})

# Domains with high regulatory importance (below critical).
HIGH_DOMAINS = frozenset({"foreign_manpower"})

# The full set of core regulatory domains to check when none are specified.
CORE_DOMAINS = [
    "employment_act",
    "cpf",
    "foreign_manpower",
    "tax",
    "wsh",
]

# Minimum number of provisions to consider a domain adequately covered.
# Fewer provisions than this threshold flags the domain as "sparse coverage".
SPARSE_THRESHOLD = 3

# Human-readable domain labels for recommendations.
_DOMAIN_LABELS = {
    "employment_act": "Employment Act",
    "cpf": "Central Provident Fund (CPF)",
    "foreign_manpower": "Foreign Manpower (EFMA)",
    "tax": "Tax / IRAS",
    "wsh": "Workplace Safety and Health (WSH)",
    "fair_employment": "Fair Employment (TAFEP / WFA)",
}


def search_provisions(domain: str, limit: int = 100) -> list[dict]:
    """Query KB provisions for a given domain.

    Thin wrapper around the KB admin ``search_provisions`` that
    standardises the call signature for compliance use cases.
    All provisions for the domain are returned (no keyword filter).
    """
    return _kb_search_provisions(query="", domain=domain, limit=limit)


def _domain_label(domain: str) -> str:
    """Return a human-readable label for a domain, falling back to the raw name."""
    return _DOMAIN_LABELS.get(domain, domain)


def _severity_for_domain(domain: str) -> str:
    """Determine gap severity based on domain criticality."""
    if domain in CRITICAL_DOMAINS:
        return "critical"
    if domain in HIGH_DOMAINS:
        return "high"
    return "medium"


def _remediation_for_domain(domain: str, provisions_found: int) -> str:
    """Build a remediation recommendation string for a domain gap."""
    label = _domain_label(domain)
    if provisions_found == 0:
        return (
            f"No {label} provisions found in the knowledge base. "
            f"Load the relevant legislation and guidelines for {label} "
            f"to enable compliance checking."
        )
    return (
        f"Only {provisions_found} {label} provision(s) found -- coverage is sparse. "
        f"Review and expand {label} provisions in the knowledge base "
        f"to ensure comprehensive compliance checking."
    )


def _query_domain_provisions(domain: str, limit: int = 100) -> list[dict]:
    """Query KB provisions for a domain, returning an empty list on failure.

    Wraps search_provisions with error handling so that a database
    outage does not crash the endpoint.
    """
    try:
        return search_provisions(domain, limit=limit)
    except Exception as exc:
        logger.warning(
            "Failed to query provisions for domain '%s': %s",
            domain,
            exc,
        )
        return []


def _classify_status(
    domain_counts: dict[str, int],
    domains: list[str],
) -> str:
    """Classify overall compliance status from per-domain provision counts.

    Returns:
        "compliant"     -- all requested domains have provisions
        "non_compliant" -- a critical domain has zero provisions
        "review_needed" -- a non-critical domain has zero provisions
    """
    missing_domains = [d for d in domains if domain_counts.get(d, 0) == 0]

    if not missing_domains:
        return "compliant"

    # Any critical domain missing -> non_compliant
    if any(d in CRITICAL_DOMAINS for d in missing_domains):
        return "non_compliant"

    return "review_needed"


def _risk_tier_from_status(status: str) -> str:
    """Map compliance status to a risk tier colour."""
    if status == "compliant":
        return "green"
    if status == "review_needed":
        return "amber"
    return "red"


# ------------------------------------------------------------------
# GET /domains
# ------------------------------------------------------------------


@router.get("/domains")
async def list_compliance_domains(
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """List all compliance domains with their labels and criticality.

    Returns the regulatory domains used for compliance checking,
    along with human-readable labels and severity classification.
    """
    domains = []
    for domain in CORE_DOMAINS:
        domains.append(
            {
                "domain_id": domain,
                "label": _domain_label(domain),
                "criticality": (
                    "critical"
                    if domain in CRITICAL_DOMAINS
                    else "high" if domain in HIGH_DOMAINS else "standard"
                ),
            }
        )

    return {
        "domains": domains,
        "total": len(domains),
    }


# ------------------------------------------------------------------
# POST /check
# ------------------------------------------------------------------


@router.post("/check")
async def compliance_check(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Run a compliance check against applicable regulations.

    Queries the knowledge base for provisions in each requested
    domain, counts coverage, and classifies overall compliance.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"compliance_check:{user_id}", max_requests=30, window_seconds=60, action_name="compliance check")
    body = await request.json()
    company_id = body.get("company_id")
    validate_company_access(current_user, requested_company_id=company_id)

    check_domains: list[str] = body.get("domains") or list(CORE_DOMAINS)

    kb_error = False
    domain_counts: dict[str, int] = {}
    findings: list[dict[str, Any]] = []

    for domain in check_domains:
        try:
            provisions = search_provisions(domain, limit=100)
        except Exception as exc:
            logger.warning(
                "KB unavailable for domain '%s' during compliance check: %s",
                domain,
                exc,
            )
            provisions = []
            kb_error = True

        count = len(provisions)
        domain_counts[domain] = count

        finding_status = "covered" if count > 0 else "missing"
        findings.append(
            {
                "domain": domain,
                "status": finding_status,
                "provisions_checked": count,
                "gaps": 0 if count > 0 else 1,
            }
        )

    status = _classify_status(domain_counts, check_domains)

    # If the KB was unreachable for every domain, force non_compliant
    if kb_error and all(c == 0 for c in domain_counts.values()):
        status = "non_compliant"

    risk_tier = _risk_tier_from_status(status)

    # Build recommendations for domains with gaps
    recommendations: list[str] = []
    for domain in check_domains:
        count = domain_counts.get(domain, 0)
        if count == 0:
            recommendations.append(_remediation_for_domain(domain, count))

    if kb_error:
        recommendations.append(
            "Knowledge base query encountered errors. "
            "Verify database connectivity and retry the compliance check."
        )

    result: dict[str, Any] = {
        "company_id": company_id,
        "domains_checked": check_domains,
        "status": status,
        "findings": findings,
        "risk_tier": risk_tier,
        "recommendations": recommendations,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    if kb_error:
        result["error"] = "One or more knowledge base queries failed. Results may be incomplete."

    logger.info(
        "Compliance check for company_id=%s: status=%s, domains=%s",
        company_id,
        status,
        check_domains,
    )

    return result


# ------------------------------------------------------------------
# GET /status/{company_id}
# ------------------------------------------------------------------


@router.get("/status/{company_id}")
async def compliance_status(
    company_id: int,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Get the latest compliance status for a company.

    Runs a simplified check across core regulatory domains and
    reports per-domain coverage from the knowledge base.
    """
    validate_company_access(current_user, requested_company_id=company_id)

    # Check cache first
    cached = _get_cached_compliance(company_id)
    if cached:
        return cached

    # Retrieve total provision count from KB stats
    total_provisions = 0
    try:
        stats = get_kb_stats()
        total_provisions = stats.get("provisions", 0)
    except Exception as exc:
        logger.warning("Failed to retrieve KB stats for compliance status: %s", exc)

    # Check each core domain
    domains_result: dict[str, dict[str, Any]] = {}
    all_covered = True
    any_critical_missing = False

    for domain in CORE_DOMAINS:
        provisions = _query_domain_provisions(domain, limit=100)
        count = len(provisions)
        if count == 0:
            domain_status = "missing"
            all_covered = False
            if domain in CRITICAL_DOMAINS:
                any_critical_missing = True
        elif count < SPARSE_THRESHOLD:
            domain_status = "sparse"
            all_covered = False
        else:
            domain_status = "covered"

        domains_result[domain] = {
            "status": domain_status,
            "provisions_count": count,
        }

    if any_critical_missing:
        overall_status = "non_compliant"
    elif all_covered:
        overall_status = "compliant"
    else:
        overall_status = "review_needed"

    logger.info(
        "Compliance status for company_id=%s: overall=%s, total_provisions=%d",
        company_id,
        overall_status,
        total_provisions,
    )

    result = {
        "company_id": company_id,
        "overall_status": overall_status,
        "last_check": datetime.now(timezone.utc).isoformat(),
        "total_provisions": total_provisions,
        "domains": domains_result,
    }
    _set_cached_compliance(company_id, result)
    return result


# ------------------------------------------------------------------
# POST /gap-analysis
# ------------------------------------------------------------------


@router.post("/gap-analysis")
async def gap_analysis(
    request: Request,
    current_user: dict = Depends(require_role("owner", "hr_manager")),
) -> dict:
    """Run a detailed gap analysis comparing KB coverage to requirements.

    Returns specific domains with missing or sparse provision coverage,
    along with severity classification and remediation recommendations.
    """
    user_id = int(current_user.get("sub", 0))
    check_rate_limit(f"gap_analysis:{user_id}", max_requests=30, window_seconds=60, action_name="gap analysis")
    body = await request.json()
    company_id = body.get("company_id")
    validate_company_access(current_user, requested_company_id=company_id)

    analyze_domains: list[str] = body.get("domains") or list(CORE_DOMAINS)

    gaps: list[dict[str, Any]] = []
    total_gaps = 0
    critical_gaps = 0

    for domain in analyze_domains:
        provisions = _query_domain_provisions(domain, limit=100)
        count = len(provisions)

        if count == 0:
            severity = _severity_for_domain(domain)
            gap_entry: dict[str, Any] = {
                "domain": domain,
                "severity": severity,
                "provisions_found": count,
                "reason": f"No provisions found for {_domain_label(domain)}",
                "remediation": _remediation_for_domain(domain, count),
            }
            gaps.append(gap_entry)
            total_gaps += 1
            if severity == "critical":
                critical_gaps += 1

        elif count < SPARSE_THRESHOLD:
            severity = _severity_for_domain(domain)
            gap_entry = {
                "domain": domain,
                "severity": severity,
                "provisions_found": count,
                "reason": f"Sparse coverage for {_domain_label(domain)} -- only {count} provision(s)",
                "remediation": _remediation_for_domain(domain, count),
            }
            gaps.append(gap_entry)
            total_gaps += 1
            if severity == "critical":
                critical_gaps += 1

    logger.info(
        "Gap analysis for company_id=%s: total_gaps=%d, critical_gaps=%d, domains=%s",
        company_id,
        total_gaps,
        critical_gaps,
        analyze_domains,
    )

    return {
        "company_id": company_id,
        "domains_analyzed": analyze_domains,
        "gaps": gaps,
        "total_gaps": total_gaps,
        "critical_gaps": critical_gaps,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
