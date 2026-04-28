"""Unit tests for the source citation and authority level system.

Tests citation validation against the KB, authority level classification,
stale citation warnings, and DB-backed provision lookup with caching.
"""

from __future__ import annotations

import time
from unittest.mock import patch

from hr_advisory.trust.citation_validator import (
    AuthorityLevel,
    CitationStatus,
    _FALLBACK_PROVISIONS,
    get_provision_detail,
    get_valid_provisions,
    validate_citations,
)


class TestCitationValidation:
    """Test citation validation against the KB."""

    def test_valid_provision(self) -> None:
        """A known provision ID should validate successfully."""
        result = validate_citations(["EA-S95-KETs"])
        assert result.is_valid is True
        assert result.valid_count == 1
        assert result.invalid_count == 0

    def test_invalid_provision(self) -> None:
        """An unknown provision ID should fail validation."""
        result = validate_citations(["NONEXISTENT-PROVISION"])
        assert result.is_valid is False
        assert result.invalid_count == 1
        assert "NONEXISTENT-PROVISION" in result.invalid_citations

    def test_mixed_valid_invalid(self) -> None:
        """Mix of valid and invalid provisions should fail overall."""
        result = validate_citations(["EA-S95-KETs", "FAKE-PROVISION"])
        assert result.is_valid is False
        assert result.valid_count == 1
        assert result.invalid_count == 1

    def test_multiple_valid_provisions(self) -> None:
        """Multiple valid provisions should all validate."""
        result = validate_citations(["EA-S95-KETs", "EA-S88A-payslip", "CPFA-S52"])
        assert result.is_valid is True
        assert result.valid_count == 3

    def test_empty_list(self) -> None:
        """Empty provision list should be valid (no citations to fail)."""
        result = validate_citations([])
        assert result.is_valid is True
        assert result.valid_count == 0

    def test_authority_level_statutory(self) -> None:
        """Statutory provisions should have STATUTORY authority level."""
        result = validate_citations(["EA-S95-KETs"])
        citation = result.validated_citations[0]
        assert citation.authority_level == AuthorityLevel.STATUTORY

    def test_authority_level_tripartite(self) -> None:
        """TGFEP provisions should have TRIPARTITE_GUIDELINE authority level."""
        result = validate_citations(["TGFEP-fair-employment"])
        citation = result.validated_citations[0]
        assert citation.authority_level == AuthorityLevel.TRIPARTITE_GUIDELINE

    def test_citation_status_valid(self) -> None:
        """Recently verified provisions should have VALID status."""
        result = validate_citations(["EA-S95-KETs"])
        citation = result.validated_citations[0]
        assert citation.status == CitationStatus.VALID

    def test_citation_title_populated(self) -> None:
        """Validated citations should have a title."""
        result = validate_citations(["EA-S95-KETs"])
        citation = result.validated_citations[0]
        assert "Key Employment Terms" in citation.title


class TestProvisionDetail:
    """Test provision detail retrieval for 'View Source' action."""

    def setup_method(self) -> None:
        """Clear the module-level provision cache.

        Other tests in the suite (advisory engine, KB search) may have warmed
        the cache with a partial DataFlow result that fails strict validation.
        Forcing a fresh load makes this self-consistency test reliable in any
        run order.
        """
        import hr_advisory.trust.citation_validator as mod

        mod._provision_cache = None
        mod._cache_timestamp = 0.0

    def test_known_provision(self) -> None:
        """Known provision should return full detail."""
        detail = get_provision_detail("EA-S95-KETs")
        assert detail is not None
        assert detail["provision_id"] == "EA-S95-KETs"
        assert "title" in detail
        assert "authority_level" in detail

    def test_unknown_provision(self) -> None:
        """Unknown provision should return None."""
        detail = get_provision_detail("DOES-NOT-EXIST")
        assert detail is None

    def test_all_kb_provisions_validate(self) -> None:
        """Every provision available via get_valid_provisions() should self-validate."""
        provisions = get_valid_provisions()
        all_ids = list(provisions.keys())
        result = validate_citations(all_ids)
        assert result.is_valid is True
        assert result.valid_count == len(all_ids)


class TestGetValidProvisions:
    """Test the DB-backed provision lookup with caching."""

    def setup_method(self) -> None:
        """Clear the provision cache before each test."""
        import hr_advisory.trust.citation_validator as mod

        mod._provision_cache = None
        mod._cache_timestamp = 0.0

    def test_returns_provisions_from_db_when_available(self) -> None:
        """When the DB query succeeds, provisions come from the DB."""
        fake_db_provisions = [
            {
                "provision_id": "TEST-PROV-1",
                "title": "Test Provision One",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
            },
            {
                "provision_id": "TEST-PROV-2",
                "title": "Test Provision Two",
                "authority_level": "tripartite_guideline",
                "effective_date": "2024-06-01",
                "last_verified": "2026-02-15",
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ):
            result = get_valid_provisions()

        assert "TEST-PROV-1" in result
        assert "TEST-PROV-2" in result
        assert result["TEST-PROV-1"]["title"] == "Test Provision One"

    def test_returns_dict_keyed_by_provision_id(self) -> None:
        """The returned dict must be keyed by provision_id, merging DB + fallback."""
        fake_db_provisions = [
            {
                "provision_id": "MY-ID-123",
                "title": "A Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ):
            result = get_valid_provisions()

        assert "MY-ID-123" in result
        # DB provisions are merged with fallback, so total >= fallback + 1
        assert len(result) >= len(_FALLBACK_PROVISIONS) + 1

    def test_cache_prevents_repeated_db_calls(self) -> None:
        """Second call within TTL should use the cache, not call DB again."""
        fake_db_provisions = [
            {
                "provision_id": "CACHED-1",
                "title": "Cached Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ) as mock_fetch:
            first_result = get_valid_provisions()
            second_result = get_valid_provisions()

        # DB should only be called once
        assert mock_fetch.call_count == 1
        # Both calls should return the same data
        assert first_result == second_result
        assert "CACHED-1" in second_result

    def test_cache_expires_after_ttl(self) -> None:
        """After the TTL elapses, the cache should be refreshed from DB."""
        import hr_advisory.trust.citation_validator as mod

        first_provisions = [
            {
                "provision_id": "OLD-1",
                "title": "Old Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
            },
        ]
        second_provisions = [
            {
                "provision_id": "NEW-1",
                "title": "New Provision",
                "authority_level": "statutory",
                "effective_date": "2025-06-01",
                "last_verified": "2026-03-10",
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            side_effect=[first_provisions, second_provisions],
        ) as mock_fetch:
            first_result = get_valid_provisions()
            assert "OLD-1" in first_result

            # Simulate TTL expiry by backdating the cache timestamp
            mod._cache_timestamp = time.time() - mod._CACHE_TTL - 1

            second_result = get_valid_provisions()
            assert "NEW-1" in second_result

        assert mock_fetch.call_count == 2

    def test_fallback_when_db_unavailable_no_stale_cache(self) -> None:
        """When DB raises and no stale cache exists, use fallback provisions."""
        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            side_effect=Exception("DB connection refused"),
        ):
            result = get_valid_provisions()

        # Should return the fallback provisions
        assert len(result) > 0
        assert result is _FALLBACK_PROVISIONS

    def test_stale_cache_preferred_over_fallback(self) -> None:
        """When DB raises but stale cache exists, prefer stale cache over fallback."""
        import hr_advisory.trust.citation_validator as mod

        stale_provisions = [
            {
                "provision_id": "STALE-1",
                "title": "Stale Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-01-01",
            },
        ]

        # First call: populate cache from DB
        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=stale_provisions,
        ):
            get_valid_provisions()

        # Expire the cache
        mod._cache_timestamp = time.time() - mod._CACHE_TTL - 1

        # Second call: DB fails, should use stale cache
        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            side_effect=Exception("DB down"),
        ):
            result = get_valid_provisions()

        assert "STALE-1" in result
        assert result is not _FALLBACK_PROVISIONS

    def test_fallback_provisions_contain_core_entries(self) -> None:
        """Fallback provisions should contain the most critical core entries."""
        assert "EA-S95-KETs" in _FALLBACK_PROVISIONS
        assert "EA-S88A-payslip" in _FALLBACK_PROVISIONS
        assert "EA-S10-notice" in _FALLBACK_PROVISIONS
        assert "CPFA-S52" in _FALLBACK_PROVISIONS
        assert "EFMA-conditions" in _FALLBACK_PROVISIONS
        assert "TGFEP-fair-employment" in _FALLBACK_PROVISIONS
        assert "WSHA-S12" in _FALLBACK_PROVISIONS

    def test_validate_citations_uses_dynamic_provisions(self) -> None:
        """validate_citations() should use get_valid_provisions(), not a static dict."""
        fake_db_provisions = [
            {
                "provision_id": "DYNAMIC-NEW",
                "title": "Dynamically Added Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
                "authority": AuthorityLevel.STATUTORY,
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ):
            result = validate_citations(["DYNAMIC-NEW"])

        assert result.is_valid is True
        assert result.valid_count == 1
        assert result.validated_citations[0].provision_id == "DYNAMIC-NEW"

    def test_get_provision_detail_uses_dynamic_provisions(self) -> None:
        """get_provision_detail() should use get_valid_provisions(), not a static dict."""
        fake_db_provisions = [
            {
                "provision_id": "DETAIL-DYN",
                "title": "Detail Dynamic Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
                "authority": AuthorityLevel.STATUTORY,
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ):
            detail = get_provision_detail("DETAIL-DYN")

        assert detail is not None
        assert detail["provision_id"] == "DETAIL-DYN"
        assert detail["title"] == "Detail Dynamic Provision"

    def test_db_provisions_without_provision_id_use_id_field(self) -> None:
        """DB records that use 'id' instead of 'provision_id' should still work."""
        fake_db_provisions = [
            {
                "id": "ALT-ID-FIELD",
                "title": "Alt ID Provision",
                "authority_level": "statutory",
                "effective_date": "2025-01-01",
                "last_verified": "2026-03-01",
            },
        ]

        with patch(
            "hr_advisory.trust.citation_validator._fetch_provisions_from_db",
            return_value=fake_db_provisions,
        ):
            result = get_valid_provisions()

        assert "ALT-ID-FIELD" in result
