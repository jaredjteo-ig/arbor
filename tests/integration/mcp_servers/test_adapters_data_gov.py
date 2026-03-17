"""Integration tests for the data.gov.sg API adapter.

Tests:
- Public holidays fetch and parsing with mocked httpx
- CPF rates fetch and parsing with mocked httpx
- In-memory caching (second call returns cached, no HTTP request)
- Cache expiry
- API error handling (500, timeout)
"""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import httpx
import pytest
import pytest_asyncio

from hr_advisory.mcp_servers.adapters.data_gov_sg import DataGovSGAdapter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def adapter() -> DataGovSGAdapter:
    """Fresh adapter with short TTLs for testing cache expiry."""
    return DataGovSGAdapter(
        api_key="test_api_key",
        holiday_cache_ttl=2,  # 2 seconds for fast cache expiry tests
        cpf_rate_cache_ttl=2,
    )


def _holidays_response(year: int = 2026) -> dict:
    """Fake data.gov.sg response for public holidays."""
    return {
        "success": True,
        "result": {
            "records": [
                {"date": f"{year}-01-01", "day": "Thursday", "holiday": "New Year's Day"},
                {"date": f"{year}-01-29", "day": "Wednesday", "holiday": "Chinese New Year"},
                {"date": f"{year}-01-30", "day": "Thursday", "holiday": "Chinese New Year"},
                {"date": f"{year}-04-03", "day": "Friday", "holiday": "Good Friday"},
                {"date": f"{year}-05-01", "day": "Friday", "holiday": "Labour Day"},
                {"date": f"{year}-08-09", "day": "Sunday", "holiday": "National Day"},
                {"date": f"{year}-12-25", "day": "Friday", "holiday": "Christmas Day"},
            ],
        },
    }


def _cpf_response() -> dict:
    """Fake data.gov.sg response for CPF rates."""
    return {
        "success": True,
        "result": {
            "records": [
                {
                    "year_of_implementation": "2026",
                    "employee_age_group": "55 and below",
                    "employer_contribution_rate": 17.0,
                    "employee_contribution_rate": 20.0,
                    "total_contribution_rate": 37.0,
                    "ordinary_account": 23.0,
                    "special_account": 6.0,
                    "medisave_account": 8.0,
                },
                {
                    "year_of_implementation": "2026",
                    "employee_age_group": "Above 55 to 60",
                    "employer_contribution_rate": 15.0,
                    "employee_contribution_rate": 16.0,
                    "total_contribution_rate": 31.0,
                    "ordinary_account": 12.0,
                    "special_account": 3.5,
                    "medisave_account": 10.5,
                },
            ],
        },
    }


def _make_mock_response(json_data: dict, status_code: int = 200) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("GET", "https://data.gov.sg/api/action/datastore_search"),
    )
    return response


# ---------------------------------------------------------------------------
# Public Holidays Tests
# ---------------------------------------------------------------------------


class TestPublicHolidays:
    """Fetch and parse public holidays from data.gov.sg."""

    @pytest.mark.asyncio
    async def test_fetch_holidays_parses_records(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            holidays = await adapter.fetch_public_holidays(2026)

        assert isinstance(holidays, list)
        assert len(holidays) == 7

    @pytest.mark.asyncio
    async def test_holiday_record_structure(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            holidays = await adapter.fetch_public_holidays(2026)

        first = holidays[0]
        assert "date" in first
        assert "day" in first
        assert "holiday" in first

    @pytest.mark.asyncio
    async def test_holidays_sorted_by_date(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            holidays = await adapter.fetch_public_holidays(2026)

        dates = [h["date"] for h in holidays]
        assert dates == sorted(dates)

    @pytest.mark.asyncio
    async def test_new_year_first_holiday(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            holidays = await adapter.fetch_public_holidays(2026)

        assert holidays[0]["holiday"] == "New Year's Day"
        assert holidays[0]["date"] == "2026-01-01"

    @pytest.mark.asyncio
    async def test_filters_to_requested_year(self, adapter):
        """Records from other years are excluded."""
        mixed_response = {
            "success": True,
            "result": {
                "records": [
                    {"date": "2025-01-01", "day": "Wednesday", "holiday": "New Year's Day"},
                    {"date": "2026-01-01", "day": "Thursday", "holiday": "New Year's Day"},
                    {"date": "2027-01-01", "day": "Friday", "holiday": "New Year's Day"},
                ],
            },
        }
        mock_response = _make_mock_response(mixed_response)
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            holidays = await adapter.fetch_public_holidays(2026)

        assert len(holidays) == 1
        assert holidays[0]["date"] == "2026-01-01"


# ---------------------------------------------------------------------------
# CPF Rates Tests
# ---------------------------------------------------------------------------


class TestCPFRates:
    """Fetch and parse CPF contribution rates."""

    @pytest.mark.asyncio
    async def test_fetch_cpf_rates_parses_records(self, adapter):
        mock_response = _make_mock_response(_cpf_response())
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            rates = await adapter.fetch_cpf_rates()

        assert isinstance(rates, list)
        assert len(rates) == 2

    @pytest.mark.asyncio
    async def test_cpf_rate_fields_normalized(self, adapter):
        mock_response = _make_mock_response(_cpf_response())
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            rates = await adapter.fetch_cpf_rates()

        first = rates[0]
        assert first["year"] == "2026"
        assert first["age_group"] == "55 and below"
        assert first["employer_contribution_rate"] == 17.0
        assert first["employee_contribution_rate"] == 20.0
        assert first["total_contribution_rate"] == 37.0

    @pytest.mark.asyncio
    async def test_cpf_rates_include_account_breakdown(self, adapter):
        mock_response = _make_mock_response(_cpf_response())
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            rates = await adapter.fetch_cpf_rates()

        first = rates[0]
        assert first["ordinary_account"] == 23.0
        assert first["special_account"] == 6.0
        assert first["medisave_account"] == 8.0


# ---------------------------------------------------------------------------
# Caching Tests
# ---------------------------------------------------------------------------


class TestCaching:
    """In-memory cache behavior."""

    @pytest.mark.asyncio
    async def test_second_call_uses_cache(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        call_count = 0

        original_get = httpx.AsyncClient.get

        async def counting_get(self_client, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch("httpx.AsyncClient.get", counting_get):
            await adapter.fetch_public_holidays(2026)
            await adapter.fetch_public_holidays(2026)

        assert call_count == 1, "Second call should use cache, not make HTTP request"

    @pytest.mark.asyncio
    async def test_cache_stats(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            await adapter.fetch_public_holidays(2026)

        stats = adapter.get_cache_stats()
        assert stats["total_entries"] >= 1
        assert stats["active_entries"] >= 1
        assert stats["expired_entries"] == 0

    @pytest.mark.asyncio
    async def test_clear_cache(self, adapter):
        mock_response = _make_mock_response(_holidays_response(2026))
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            await adapter.fetch_public_holidays(2026)

        cleared = adapter.clear_cache()
        assert cleared >= 1
        assert adapter.get_cache_stats()["total_entries"] == 0

    @pytest.mark.asyncio
    async def test_cache_expiry_triggers_new_fetch(self, adapter):
        """After TTL expires, a new HTTP request is made."""
        mock_response = _make_mock_response(_holidays_response(2026))
        call_count = 0

        async def counting_get(self_client, *args, **kwargs):
            nonlocal call_count
            call_count += 1
            return mock_response

        with patch("httpx.AsyncClient.get", counting_get):
            await adapter.fetch_public_holidays(2026)
            assert call_count == 1

            # Manually expire the cache by manipulating the expiry
            for entry in adapter._cache.values():
                entry.expires_at = time.monotonic() - 1

            await adapter.fetch_public_holidays(2026)
            assert call_count == 2, "Expired cache should trigger a new fetch"


# ---------------------------------------------------------------------------
# Error Handling Tests
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """API error responses and timeouts."""

    @pytest.mark.asyncio
    async def test_http_500_raises(self, adapter):
        error_response = httpx.Response(
            status_code=500,
            text="Internal Server Error",
            request=httpx.Request("GET", "https://data.gov.sg/api/action/datastore_search"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=error_response):
            with pytest.raises(httpx.HTTPStatusError):
                await adapter.fetch_public_holidays(2026)

    @pytest.mark.asyncio
    async def test_timeout_raises(self, adapter):
        async def timeout_side_effect(*args, **kwargs):
            raise httpx.ReadTimeout("Connection timed out")

        with patch(
            "httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=timeout_side_effect
        ):
            with pytest.raises(httpx.ReadTimeout):
                await adapter.fetch_public_holidays(2026)

    @pytest.mark.asyncio
    async def test_success_false_raises(self, adapter):
        bad_response = _make_mock_response(
            {"success": False, "error": {"message": "Resource not found"}}
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=bad_response):
            with pytest.raises(ValueError, match="success=false"):
                await adapter.fetch_public_holidays(2026)


# ---------------------------------------------------------------------------
# CPF Rate Discrepancy Check
# ---------------------------------------------------------------------------


class TestCPFRateDiscrepancy:
    """Check hardcoded rates against live data.gov.sg rates."""

    @pytest.mark.asyncio
    async def test_no_discrepancy_when_rates_match(self, adapter):
        mock_response = _make_mock_response(_cpf_response())
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            discrepancies = await adapter.check_cpf_rate_discrepancies(
                {
                    "55 and below": {"employer": 17.0, "employee": 20.0, "total": 37.0},
                }
            )
        assert discrepancies == []

    @pytest.mark.asyncio
    async def test_discrepancy_detected_when_rates_differ(self, adapter):
        mock_response = _make_mock_response(_cpf_response())
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            discrepancies = await adapter.check_cpf_rate_discrepancies(
                {
                    "55 and below": {"employer": 16.0, "employee": 20.0, "total": 36.0},
                }
            )
        assert len(discrepancies) >= 1
        fields = {d["field"] for d in discrepancies}
        assert "employer" in fields


# ---------------------------------------------------------------------------
# Date Parsing
# ---------------------------------------------------------------------------


class TestDateParsing:
    """Verify _parse_date handles multiple formats."""

    def test_iso_format(self, adapter):
        from hr_advisory.mcp_servers.adapters.data_gov_sg import DataGovSGAdapter

        d = DataGovSGAdapter._parse_date("2026-03-25")
        assert d is not None
        assert d.isoformat() == "2026-03-25"

    def test_dd_mm_yyyy_slash(self, adapter):
        d = DataGovSGAdapter._parse_date("25/03/2026")
        assert d is not None
        assert d.isoformat() == "2026-03-25"

    def test_invalid_date_returns_none(self, adapter):
        d = DataGovSGAdapter._parse_date("not-a-date")
        assert d is None

    def test_empty_string_returns_none(self, adapter):
        d = DataGovSGAdapter._parse_date("")
        assert d is None


# ---------------------------------------------------------------------------
# Rate Parsing
# ---------------------------------------------------------------------------


class TestRateParsing:
    """Verify _parse_rate handles various formats."""

    def test_float_value(self):
        assert DataGovSGAdapter._parse_rate(17.0) == 17.0

    def test_int_value(self):
        assert DataGovSGAdapter._parse_rate(17) == 17.0

    def test_string_percentage(self):
        assert DataGovSGAdapter._parse_rate("17.0%") == 17.0

    def test_dash_returns_none(self):
        assert DataGovSGAdapter._parse_rate("-") is None

    def test_empty_string_returns_none(self):
        assert DataGovSGAdapter._parse_rate("") is None

    def test_none_returns_none(self):
        assert DataGovSGAdapter._parse_rate(None) is None
