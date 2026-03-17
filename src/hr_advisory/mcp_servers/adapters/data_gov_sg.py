"""Data.gov.sg API adapter for public holidays and CPF rate data.

Connectors G08 (Public Holidays) and G09 (CPF Rates) from the
aite-regulatory MCP server. Fetches live government data with
TTL-based caching to replace hardcoded values.

T214: Data.gov.sg Public Holidays Connector
T215: Data.gov.sg CPF Rate Monitor
"""

from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import date, datetime, timezone
from typing import Any, Optional

import httpx

from hr_advisory.mcp_servers.resilience import check_rate_limit, get_circuit

logger = logging.getLogger(__name__)

# data.gov.sg dataset resource IDs
_HOLIDAYS_RESOURCE_ID = "d_149b61ad0a22f61c09dc80f2df5bbec8"
_CPF_RATES_RESOURCE_ID = "d_98ffa142ae0dec40391f78f81d26aca9"

_BASE_URL = "https://data.gov.sg/api/action/datastore_search"

_PROVIDER_NAME = "data_gov_sg"


class _CacheEntry:
    """Single in-memory cache entry with TTL."""

    __slots__ = ("data", "etag", "expires_at")

    def __init__(self, data: Any, ttl_seconds: int, etag: str = ""):
        self.data = data
        self.etag = etag
        self.expires_at = time.monotonic() + ttl_seconds

    @property
    def is_expired(self) -> bool:
        return time.monotonic() >= self.expires_at


class DataGovSGAdapter:
    """Adapter for Singapore's data.gov.sg open data API.

    Provides live government data for public holidays and CPF
    contribution rates. All responses are cached in memory with
    configurable TTL to stay within the 30-calls-per-10-seconds
    rate limit.

    Usage::

        adapter = DataGovSGAdapter()
        holidays = await adapter.fetch_public_holidays(2026)
        rates = await adapter.fetch_cpf_rates()
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        holiday_cache_ttl: int = 86400,  # 24 hours
        cpf_rate_cache_ttl: int = 604800,  # 7 days
    ):
        self._api_key = api_key or os.environ.get("DATA_GOV_SG_API_KEY", "")
        self._holiday_cache_ttl = holiday_cache_ttl
        self._cpf_rate_cache_ttl = cpf_rate_cache_ttl
        self._cache: dict[str, _CacheEntry] = {}
        self._circuit = get_circuit("data_gov_sg")

    def _headers(self) -> dict[str, str]:
        headers = {
            "User-Agent": "AITE-HR-Advisory/1.0 (+https://aite.sg)",
            "Accept": "application/json",
        }
        if self._api_key:
            headers["x-api-key"] = self._api_key
        return headers

    def _cache_key(self, resource_id: str, params: dict) -> str:
        """Generate a deterministic cache key from resource and params."""
        raw = f"{resource_id}:{sorted(params.items())}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if entry is not None and not entry.is_expired:
            return entry.data
        if entry is not None and entry.is_expired:
            del self._cache[key]
        return None

    def _set_cached(self, key: str, data: Any, ttl: int) -> None:
        self._cache[key] = _CacheEntry(data=data, ttl_seconds=ttl)

    async def _fetch(
        self,
        resource_id: str,
        extra_params: Optional[dict] = None,
        limit: int = 500,
        tenant_id: str = "_global",
    ) -> dict:
        """Execute a data.gov.sg datastore_search query through the circuit breaker.

        Rate limit is enforced before each request (30 calls per 10 seconds).
        """
        # Enforce rate limit before making the API call
        check_rate_limit(tenant_id, _PROVIDER_NAME)

        params: dict[str, Any] = {"resource_id": resource_id, "limit": limit}
        if extra_params:
            params.update(extra_params)

        async def _do_fetch() -> dict:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(
                    _BASE_URL,
                    params=params,
                    headers=self._headers(),
                )
                resp.raise_for_status()
                body = resp.json()
                if not body.get("success"):
                    raise ValueError(
                        f"data.gov.sg returned success=false: {body.get('error', {}).get('message', 'unknown')}"
                    )
                return body["result"]

        return await self._circuit.call(_do_fetch)

    # -- Public Holidays (G08) -----------------------------------------

    async def fetch_public_holidays(self, year: int, tenant_id: str = "_global") -> list[dict]:
        """Fetch gazetted Singapore public holidays for a given year.

        Returns a list of dicts, each with:
            - date: ISO date string (YYYY-MM-DD)
            - day: Day of the week (e.g. "Monday")
            - holiday: Name of the holiday

        Results are cached for 24 hours.
        """
        cache_key = self._cache_key(_HOLIDAYS_RESOURCE_ID, {"year": year})
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("Public holidays for %d served from cache", year)
            return cached

        logger.info("Fetching public holidays for %d from data.gov.sg", year)
        result = await self._fetch(
            resource_id=_HOLIDAYS_RESOURCE_ID,
            extra_params={"q": str(year)},
            limit=50,
            tenant_id=tenant_id,
        )

        records = result.get("records", [])
        holidays = self._normalize_holidays(records, year)
        self._set_cached(cache_key, holidays, self._holiday_cache_ttl)
        logger.info("Cached %d public holidays for %d", len(holidays), year)
        return holidays

    def _normalize_holidays(self, records: list[dict], year: int) -> list[dict]:
        """Normalize raw data.gov.sg holiday records into a clean format.

        The dataset may include multiple years in one response, so we
        filter to the requested year. Field names may vary across
        dataset revisions, so we handle common variants.
        """
        holidays: list[dict] = []
        for rec in records:
            # Handle different field name conventions in the dataset
            raw_date = rec.get("date") or rec.get("Date") or rec.get("DATE", "")
            holiday_name = (
                rec.get("holiday")
                or rec.get("Holiday")
                or rec.get("HOLIDAY")
                or rec.get("na_of_holiday")
                or rec.get("name")
                or ""
            )
            day_of_week = rec.get("day") or rec.get("Day") or rec.get("DAY") or ""

            if not raw_date or not holiday_name:
                continue

            # Parse the date and filter by year
            parsed_date = self._parse_date(raw_date)
            if parsed_date is None:
                continue
            if parsed_date.year != year:
                continue

            holidays.append(
                {
                    "date": parsed_date.isoformat(),
                    "day": day_of_week or parsed_date.strftime("%A"),
                    "holiday": holiday_name.strip(),
                }
            )

        # Sort by date
        holidays.sort(key=lambda h: h["date"])
        return holidays

    @staticmethod
    def _parse_date(raw: str) -> Optional[date]:
        """Parse a date string in common formats."""
        for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d"):
            try:
                return datetime.strptime(raw.strip(), fmt).date()
            except ValueError:
                continue
        return None

    # -- CPF Rates (G09) -----------------------------------------------

    async def fetch_cpf_rates(self, tenant_id: str = "_global") -> list[dict]:
        """Fetch CPF contribution rate tables from data.gov.sg.

        Returns the raw rate records. Each record typically contains:
            - year_of_implementation
            - employee_age_group (e.g. "55 and below", "Above 55 to 60")
            - employer_contribution_rate
            - employee_contribution_rate
            - total_contribution_rate
            - ordinary_account
            - special_account / retirement_account
            - medisave_account

        Results are cached for 7 days.
        """
        cache_key = self._cache_key(_CPF_RATES_RESOURCE_ID, {})
        cached = self._get_cached(cache_key)
        if cached is not None:
            logger.debug("CPF rates served from cache")
            return cached

        logger.info("Fetching CPF rates from data.gov.sg")
        result = await self._fetch(
            resource_id=_CPF_RATES_RESOURCE_ID,
            limit=500,
            tenant_id=tenant_id,
        )

        records = result.get("records", [])
        rates = self._normalize_cpf_rates(records)
        self._set_cached(cache_key, rates, self._cpf_rate_cache_ttl)
        logger.info("Cached %d CPF rate records", len(rates))
        return rates

    def _normalize_cpf_rates(self, records: list[dict]) -> list[dict]:
        """Normalize CPF rate records into a consistent format."""
        normalized: list[dict] = []
        for rec in records:
            entry: dict[str, Any] = {}

            # Extract year
            entry["year"] = (
                rec.get("year_of_implementation") or rec.get("year") or rec.get("Year") or ""
            )

            # Extract age group
            entry["age_group"] = (
                rec.get("employee_age_group") or rec.get("age_group") or rec.get("Age Group") or ""
            )

            # Extract rates — convert to float where possible
            for field in (
                "employer_contribution_rate",
                "employee_contribution_rate",
                "total_contribution_rate",
                "ordinary_account",
                "special_account",
                "retirement_account",
                "medisave_account",
            ):
                raw_val = rec.get(field) or rec.get(field.replace("_", " ").title()) or ""
                entry[field] = self._parse_rate(raw_val)

            # Keep raw record for fields we might not recognize
            entry["_raw"] = rec
            normalized.append(entry)

        return normalized

    @staticmethod
    def _parse_rate(raw: Any) -> Optional[float]:
        """Parse a rate value, handling percentages and strings."""
        if isinstance(raw, (int, float)):
            return float(raw)
        if isinstance(raw, str):
            cleaned = raw.strip().rstrip("%").strip()
            if not cleaned or cleaned == "-":
                return None
            try:
                return float(cleaned)
            except ValueError:
                return None
        return None

    async def check_cpf_rate_discrepancies(
        self,
        hardcoded_rates: dict[str, dict[str, float]],
    ) -> list[dict]:
        """Compare data.gov.sg CPF rates against hardcoded rates.

        Args:
            hardcoded_rates: Dict keyed by age_group, value is dict with
                keys "employer", "employee", "total".

        Returns:
            List of discrepancy dicts with keys:
            age_group, field, hardcoded, data_gov, difference
        """
        live_rates = await self.fetch_cpf_rates()
        if not live_rates:
            return [{"error": "No CPF rate data available from data.gov.sg"}]

        # Get the most recent year's rates
        years = {r.get("year", "") for r in live_rates if r.get("year")}
        if not years:
            return [{"error": "No year information in CPF rate data"}]

        latest_year = max(years)
        latest = [r for r in live_rates if r.get("year") == latest_year]

        discrepancies: list[dict] = []
        for rate_rec in latest:
            age_group = rate_rec.get("age_group", "")
            if age_group not in hardcoded_rates:
                continue

            hardcoded = hardcoded_rates[age_group]
            field_mapping = {
                "employer": "employer_contribution_rate",
                "employee": "employee_contribution_rate",
                "total": "total_contribution_rate",
            }

            for hc_field, live_field in field_mapping.items():
                hc_val = hardcoded.get(hc_field)
                live_val = rate_rec.get(live_field)
                if hc_val is not None and live_val is not None:
                    # Compare with tolerance for floating point
                    if abs(hc_val - live_val) > 0.01:
                        discrepancies.append(
                            {
                                "age_group": age_group,
                                "field": hc_field,
                                "hardcoded": hc_val,
                                "data_gov_sg": live_val,
                                "difference": round(live_val - hc_val, 4),
                                "year": latest_year,
                            }
                        )

        return discrepancies

    # -- Cache management ----------------------------------------------

    def clear_cache(self) -> int:
        """Clear all cached entries. Returns number of entries cleared."""
        count = len(self._cache)
        self._cache.clear()
        return count

    def get_cache_stats(self) -> dict:
        """Return cache statistics."""
        total = len(self._cache)
        expired = sum(1 for e in self._cache.values() if e.is_expired)
        return {
            "total_entries": total,
            "active_entries": total - expired,
            "expired_entries": expired,
        }
