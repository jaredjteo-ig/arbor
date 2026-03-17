"""ACRA (Accounting and Corporate Regulatory Authority) adapter.

Provides two paths for company verification:

1. **UEN Verification (free)**: Cross-references UEN against the
   data.gov.sg ACRA entity dataset (bulk, updated periodically).

2. **Business Profile (paid)**: Full company profile via the ACRA
   Business Profile API (S$5.50 per query, real-time).

ACRA Business Profile API (launched Nov 2025):
- Endpoint: https://api.apex.gov.sg/acra/v1/business-profile
- Auth: CorpPass via APEX
- Returns: Entity name, status, SSIC codes, directors, shareholders,
  registered address, capital, date of incorporation

Data.gov.sg ACRA dataset:
- Endpoint: https://data.gov.sg/api/action/datastore_search
- Resource ID: Entities registered/deregistered dataset
- Auth: API key (x-api-key header)
- Free, rate-limited (30 calls/10s)

Reference:
- ACRA BizFile+ portal (bizfile.gov.sg)
- data.gov.sg API documentation
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.auth.corppass import CorpPassError, get_valid_token
from hr_advisory.mcp_servers.health import get_health_monitor
from hr_advisory.mcp_servers.resilience import RATE_LIMITERS, RateLimiter, get_circuit

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

APEX_BASE_URL = os.environ.get("APEX_BASE_URL", "https://api.apex.gov.sg")
APEX_BASE_URL_SANDBOX = os.environ.get("APEX_BASE_URL_SANDBOX", "https://sandbox.api.apex.gov.sg")
APEX_USE_SANDBOX = os.environ.get("APEX_USE_SANDBOX", "true").lower() == "true"
APEX_API_KEY = os.environ.get("APEX_API_KEY", "")

ACRA_PROFILE_PATH = "/acra/v1/business-profile"

DATA_GOV_SG_URL = os.environ.get(
    "DATA_GOV_SG_URL",
    "https://data.gov.sg/api/action/datastore_search",
)
DATA_GOV_SG_API_KEY = os.environ.get("DATA_GOV_SG_API_KEY", "")

# ACRA entity dataset resource IDs on data.gov.sg
ACRA_ENTITY_RESOURCE_ID = os.environ.get(
    "ACRA_ENTITY_RESOURCE_ID",
    "d_f2c8a3d7f4b5e1a6d0c9b8e7f3a2d1c0",  # Placeholder — actual ID from data.gov.sg
)

# Cost per ACRA Business Profile query (in SGD)
ACRA_QUERY_COST = 5.50

_health = get_health_monitor()

# Rate limiter for data.gov.sg
if "data_gov_sg" not in RATE_LIMITERS:
    RATE_LIMITERS["data_gov_sg"] = RateLimiter(max_calls=30, window_seconds=10)

# ---------------------------------------------------------------------------
# In-memory cache for business profiles (30-day TTL)
# ---------------------------------------------------------------------------

_profile_cache: dict[str, dict[str, Any]] = {}  # UEN -> {data, fetched_at, source}
_CACHE_TTL = 30 * 24 * 60 * 60  # 30 days in seconds

# Cost tracking
_cost_ledger: list[dict] = []


def _get_base_url() -> str:
    return APEX_BASE_URL_SANDBOX if APEX_USE_SANDBOX else APEX_BASE_URL


# ---------------------------------------------------------------------------
# UEN Validation
# ---------------------------------------------------------------------------

# UEN format: https://www.uen.gov.sg/ueninternet/faces/pages/admin/aboutUEN.jspx
# Local Company: YYYYNNNNNX (10 chars, starts with year 1800-2099)
# Local Business: NNNNNNNNNX (10 chars, starts with digits)
# Others: TNNXXNNNNN (10 chars, starts with T/S/R)

_UEN_PATTERN = re.compile(
    r"^(?:"
    r"\d{9}[A-Z]"  # Local business (old format)
    r"|"
    r"(?:19|20)\d{7}[A-Z]"  # Local company
    r"|"
    r"[TSR]\d{2}[A-Z]{2}\d{4}[A-Z]"  # Others (e.g., T08FC1234A)
    r")$",
    re.IGNORECASE,
)


def _is_valid_uen_format(uen: str) -> bool:
    """Validate UEN format using regex. Does NOT verify existence."""
    if not uen or len(uen) < 9 or len(uen) > 10:
        return False
    return bool(_UEN_PATTERN.match(uen.upper()))


# UEN check digit algorithm for local companies (YYYYNNNNNX)
_UEN_WEIGHTS = [4, 3, 5, 2, 7, 8, 6, 4, 0]
_UEN_CHECK_CHARS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def _verify_uen_check_digit(uen: str) -> bool:
    """Verify the check digit of a Singapore UEN.

    Applies to local company UENs (YYYYNNNNNX format).
    Returns True if valid or if format doesn't support check digit validation.
    """
    uen = uen.upper()
    if len(uen) != 10:
        return False

    # Only validate local company format (starts with 19 or 20)
    if not (uen[:2] in ("19", "20") and uen[:-1].isdigit()):
        # Other formats — accept as valid if regex passes
        return True

    # Weighted sum of first 9 digits
    total = 0
    for i, ch in enumerate(uen[:9]):
        total += int(ch) * _UEN_WEIGHTS[i]

    remainder = total % 11
    expected_index = (11 - remainder) % 26
    expected_char = _UEN_CHECK_CHARS[expected_index] if expected_index < 26 else ""

    return uen[9] == expected_char


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def verify_uen(uen: str) -> dict:
    """Validate a UEN and look it up in the data.gov.sg ACRA dataset.

    This is the free path. Uses the publicly available ACRA entity
    dataset on data.gov.sg to verify that a UEN exists and retrieve
    basic entity information.

    Args:
        uen: Singapore UEN to verify.

    Returns:
        Dict with validation result, entity name, status, and type.
    """
    uen = uen.strip().upper()

    # Format validation
    if not _is_valid_uen_format(uen):
        return {
            "valid": False,
            "uen": uen,
            "error": "Invalid UEN format",
            "source": "format_check",
        }

    # Check digit validation
    if not _verify_uen_check_digit(uen):
        return {
            "valid": False,
            "uen": uen,
            "error": "UEN check digit invalid",
            "source": "checksum",
        }

    # Check cache
    cached = _profile_cache.get(uen)
    if cached and (time.time() - cached["fetched_at"]) < _CACHE_TTL:
        return {
            "valid": True,
            "uen": uen,
            "entity_name": cached["data"].get("entity_name", ""),
            "entity_type": cached["data"].get("entity_type", ""),
            "entity_status": cached["data"].get("entity_status", ""),
            "source": f"{cached['source']}_cache",
        }

    # Look up in data.gov.sg
    rate_limiter = RATE_LIMITERS.get("data_gov_sg")
    if rate_limiter and not rate_limiter.check("system", "data_gov_sg"):
        return {
            "valid": None,
            "uen": uen,
            "error": "Rate limited — please retry in a few seconds",
            "source": "rate_limited",
        }

    circuit = get_circuit("data_gov_sg")

    try:

        async def _lookup() -> dict:
            headers = {"Accept": "application/json"}
            if DATA_GOV_SG_API_KEY:
                headers["x-api-key"] = DATA_GOV_SG_API_KEY

            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(
                    DATA_GOV_SG_URL,
                    params={
                        "resource_id": ACRA_ENTITY_RESOURCE_ID,
                        "q": uen,
                        "limit": 5,
                    },
                    headers=headers,
                )
                if resp.status_code != 200:
                    raise Exception(f"data.gov.sg returned HTTP {resp.status_code}")
                return resp.json()

        result = await circuit.call(_lookup)

        _health.record_success("data_gov_sg")

        # Parse results
        records = result.get("result", {}).get("records", [])

        # Find exact UEN match
        match = None
        for record in records:
            record_uen = record.get("uen", "").upper()
            if record_uen == uen:
                match = record
                break

        if match is None:
            return {
                "valid": False,
                "uen": uen,
                "error": "UEN not found in ACRA registry",
                "source": "data_gov_sg",
            }

        entity_data = {
            "entity_name": match.get("entity_name", match.get("company_name", "")),
            "entity_type": match.get("entity_type", match.get("company_type", "")),
            "entity_status": match.get("entity_status_description", match.get("status", "")),
            "ssic_code": match.get("primary_ssic_code", ""),
            "ssic_description": match.get("primary_ssic_description", ""),
            "registration_date": match.get("registration_incorporation_date", ""),
        }

        # Cache the result
        _profile_cache[uen] = {
            "data": entity_data,
            "fetched_at": time.time(),
            "source": "data_gov_sg",
        }

        return {
            "valid": True,
            "uen": uen,
            "entity_name": entity_data["entity_name"],
            "entity_type": entity_data["entity_type"],
            "entity_status": entity_data["entity_status"],
            "ssic_code": entity_data["ssic_code"],
            "ssic_description": entity_data["ssic_description"],
            "registration_date": entity_data["registration_date"],
            "source": "data_gov_sg",
        }

    except Exception as e:
        _health.record_error("data_gov_sg", str(e))
        logger.warning("data.gov.sg lookup failed for UEN %s: %s", uen, e)

        # Fall back to format-only validation
        return {
            "valid": None,
            "uen": uen,
            "error": f"Could not verify against registry: {e}",
            "format_valid": True,
            "source": "format_check_only",
        }


async def get_business_profile(
    tenant_id: str,
    uen: str,
) -> dict:
    """Get full business profile via the ACRA API (S$5.50 per query).

    Returns comprehensive company information including directors,
    shareholders, capital, and registered address. Results are cached
    for 30 days to minimize costs.

    Args:
        tenant_id: Company/tenant ID (for CorpPass auth and cost tracking).
        uen: Singapore UEN to query.

    Returns:
        Dict with full business profile and cost information.
    """
    uen = uen.strip().upper()

    # Check cache first (30-day TTL)
    cached = _profile_cache.get(uen)
    if (
        cached
        and cached.get("source") == "acra_api"
        and (time.time() - cached["fetched_at"]) < _CACHE_TTL
    ):
        return {
            "uen": uen,
            "profile": cached["data"],
            "source": "acra_api_cache",
            "cost": 0.0,
            "cached": True,
        }

    # Get CorpPass token
    access_token = await get_valid_token(tenant_id)

    base_url = _get_base_url()
    url = f"{base_url}{ACRA_PROFILE_PATH}"

    circuit = get_circuit("acra")

    async def _fetch_profile() -> dict:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                url,
                params={"uen": uen},
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "Accept": "application/json",
                    "X-API-Key": APEX_API_KEY,
                },
            )
            if resp.status_code == 200:
                return resp.json()
            elif resp.status_code == 404:
                raise ACRAError(
                    f"UEN {uen} not found in ACRA registry",
                    error_code="uen_not_found",
                )
            else:
                raise ACRAError(
                    f"ACRA API error (HTTP {resp.status_code})",
                    error_code="acra_api_error",
                    details={"http_status": resp.status_code, "body": resp.text[:500]},
                )

    result = await circuit.call(_fetch_profile)

    _health.record_success("acra")

    # Parse ACRA response
    profile = _parse_acra_profile(result)

    # Cache result
    _profile_cache[uen] = {
        "data": profile,
        "fetched_at": time.time(),
        "source": "acra_api",
    }

    # Track cost
    cost_record = {
        "tenant_id": tenant_id,
        "uen": uen,
        "cost_sgd": ACRA_QUERY_COST,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    _cost_ledger.append(cost_record)

    logger.info(
        "ACRA profile fetched for UEN %s (cost: S$%.2f, total queries: %d)",
        uen,
        ACRA_QUERY_COST,
        len(_cost_ledger),
    )

    return {
        "uen": uen,
        "profile": profile,
        "source": "acra_api",
        "cost": ACRA_QUERY_COST,
        "cached": False,
    }


def _parse_acra_profile(raw: dict) -> dict:
    """Parse ACRA Business Profile API response into structured format."""
    entity = raw.get("entity", raw)

    def _val(field: Any) -> Any:
        if isinstance(field, dict):
            return field.get("value", field.get("desc", ""))
        return field

    # Core entity info
    profile = {
        "entity_name": _val(entity.get("entityName", entity.get("name", ""))),
        "entity_type": _val(entity.get("entityType", "")),
        "entity_status": _val(entity.get("entityStatus", entity.get("status", ""))),
        "registration_date": _val(
            entity.get("registrationDate", entity.get("incorporationDate", ""))
        ),
        "uen": _val(entity.get("uen", "")),
    }

    # SSIC codes
    primary_ssic = entity.get("primaryActivity", entity.get("primarySSIC", {}))
    secondary_ssic = entity.get("secondaryActivity", entity.get("secondarySSIC", {}))
    profile["primary_ssic"] = {
        "code": _val(primary_ssic.get("code", "")),
        "description": _val(primary_ssic.get("description", "")),
    }
    profile["secondary_ssic"] = {
        "code": _val(secondary_ssic.get("code", "")),
        "description": _val(secondary_ssic.get("description", "")),
    }

    # Registered address
    address = entity.get("registeredAddress", {})
    addr_parts = []
    for field in ("block", "streetName", "level", "unitNo", "buildingName"):
        v = _val(address.get(field, ""))
        if v:
            addr_parts.append(str(v))
    profile["registered_address"] = {
        "full_address": " ".join(addr_parts),
        "postal_code": _val(address.get("postalCode", "")),
    }

    # Capital
    capital = entity.get("paidUpCapital", entity.get("capital", {}))
    profile["paid_up_capital"] = {
        "currency": _val(capital.get("currency", "SGD")),
        "amount": _val(capital.get("amount", 0)),
        "ordinary_shares": _val(capital.get("ordinaryShares", 0)),
        "preference_shares": _val(capital.get("preferenceShares", 0)),
    }

    # Directors / Officers
    officers = entity.get("officers", entity.get("appointments", []))
    profile["directors"] = []
    for officer in officers:
        profile["directors"].append(
            {
                "name": _val(officer.get("name", "")),
                "id_no_last4": (
                    _val(officer.get("idNo", ""))[-4:] if _val(officer.get("idNo", "")) else ""
                ),
                "position": _val(officer.get("position", "")),
                "appointment_date": _val(officer.get("appointmentDate", "")),
                "nationality": _val(officer.get("nationality", "")),
            }
        )

    # Shareholders
    shareholders = entity.get("shareholders", [])
    profile["shareholders"] = []
    for sh in shareholders:
        profile["shareholders"].append(
            {
                "name": _val(sh.get("name", "")),
                "id_type": _val(sh.get("idType", "")),
                "share_type": _val(sh.get("shareType", "ORDINARY")),
                "num_shares": _val(sh.get("numShares", 0)),
            }
        )

    return profile


class ACRAError(Exception):
    """Error during ACRA API operation."""

    def __init__(
        self, message: str, error_code: str = "acra_error", details: Optional[dict] = None
    ):
        self.error_code = error_code
        self.details = details or {}
        super().__init__(message)


# ---------------------------------------------------------------------------
# Cost tracking
# ---------------------------------------------------------------------------


def get_cost_summary(tenant_id: Optional[str] = None) -> dict:
    """Get cost summary for ACRA API queries.

    Args:
        tenant_id: Optional filter by tenant.

    Returns:
        Dict with total queries, total cost, and per-tenant breakdown.
    """
    records = _cost_ledger
    if tenant_id:
        records = [r for r in records if r["tenant_id"] == tenant_id]

    total_cost = sum(r["cost_sgd"] for r in records)
    total_queries = len(records)

    # Group by tenant
    by_tenant: dict[str, float] = {}
    for r in records:
        tid = r["tenant_id"]
        by_tenant[tid] = by_tenant.get(tid, 0.0) + r["cost_sgd"]

    return {
        "total_queries": total_queries,
        "total_cost_sgd": round(total_cost, 2),
        "per_tenant": {k: round(v, 2) for k, v in by_tenant.items()},
        "cost_per_query_sgd": ACRA_QUERY_COST,
    }


def clear_cache(uen: Optional[str] = None) -> int:
    """Clear cached business profiles.

    Args:
        uen: Optional UEN to clear. If None, clears all.

    Returns:
        Number of entries cleared.
    """
    if uen:
        uen = uen.strip().upper()
        if uen in _profile_cache:
            del _profile_cache[uen]
            return 1
        return 0

    count = len(_profile_cache)
    _profile_cache.clear()
    return count
