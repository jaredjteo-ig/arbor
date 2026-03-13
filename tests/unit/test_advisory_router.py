"""Unit tests for advisory router helper functions.

Tests the _lookup_provisions and _generate_grounded_response functions
that form the KB retrieval and response generation stages of the safety chain.

Tier 1 (Unit): Fast, isolated, can use mocks for external services.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


class TestLookupProvisions:
    """Tests for _lookup_provisions — dynamic KB search for provision IDs."""

    def test_returns_list(self):
        """_lookup_provisions must always return a list."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        result = _lookup_provisions(["employment_act"], query="overtime")
        assert isinstance(result, list)

    def test_query_affects_results(self):
        """Different queries for the same domain should potentially return
        different provisions, proving the function uses the query to search."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        # Mock search_provisions to return query-specific results
        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.side_effect = lambda query, domain, limit: (
                [{"id": 1, "title": "Annual Leave"}]
                if "annual leave" in query.lower()
                else [{"id": 2, "title": "Sick Leave"}]
            )
            result_a = _lookup_provisions(["employment_act"], query="annual leave entitlement")
            result_b = _lookup_provisions(["employment_act"], query="sick leave policy")

            # The search function was called with different queries
            assert mock_search.call_count == 2
            calls = [c.kwargs.get("query") or c.args[0] for c in mock_search.call_args_list]
            # Queries passed to search should differ
            assert calls[0] != calls[1]

    def test_passes_domain_to_search(self):
        """Must map internal domain names to KB domain names for search."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 10}]
            _lookup_provisions(["cpf"], query="contribution rates")
            # Should have been called with domain="CPF"
            call_kwargs = mock_search.call_args
            assert call_kwargs.kwargs.get("domain") == "CPF" or (
                len(call_kwargs.args) > 1 and call_kwargs.args[1] == "CPF"
            )

    def test_maps_employment_act_domain(self):
        """Internal 'employment_act' maps to KB 'Employment Act'."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["employment_act"], query="overtime")
            call_kwargs = mock_search.call_args
            domain_arg = call_kwargs.kwargs.get("domain")
            assert domain_arg == "Employment Act"

    def test_maps_foreign_manpower_domain(self):
        """Internal 'foreign_manpower' maps to KB 'Foreign Manpower'."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["foreign_manpower"], query="work permit")
            call_kwargs = mock_search.call_args
            domain_arg = call_kwargs.kwargs.get("domain")
            assert domain_arg == "Foreign Manpower"

    def test_maps_fair_employment_domain(self):
        """Internal 'fair_employment' maps to KB 'Fair Employment'."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["fair_employment"], query="discrimination")
            call_kwargs = mock_search.call_args
            domain_arg = call_kwargs.kwargs.get("domain")
            assert domain_arg == "Fair Employment"

    def test_maps_wsh_domain(self):
        """Internal 'wsh' maps to KB 'Workplace Safety and Health'."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["wsh"], query="safety")
            call_kwargs = mock_search.call_args
            domain_arg = call_kwargs.kwargs.get("domain")
            assert domain_arg == "Workplace Safety and Health"

    def test_multiple_domains_searches_each(self):
        """When multiple domains are provided, searches each one."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 5}]
            result = _lookup_provisions(["employment_act", "cpf"], query="payroll")
            assert mock_search.call_count == 2

    def test_deduplicates_provision_ids(self):
        """If the same provision ID appears from multiple domain searches,
        the result should still contain it (at least once)."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 42}]
            result = _lookup_provisions(["employment_act", "cpf"], query="contribution")
            # Each domain returns id=42, so "42" should appear
            assert "42" in result

    def test_search_exception_falls_through(self):
        """If search_provisions raises, the function should not crash
        — it should gracefully fall back."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.side_effect = Exception("DB connection failed")
            # Should not raise
            result = _lookup_provisions(["employment_act"], query="overtime")
            assert isinstance(result, list)

    def test_fallback_to_citation_validator_when_no_db_results(self):
        """When search_provisions returns empty results, should fall back
        to the citation validator's _KB_PROVISIONS registry."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            result = _lookup_provisions(["employment_act"], query="overtime")
            # Should return known provision IDs from the citation validator fallback
            assert len(result) > 0
            # These are the known EA provision IDs in _KB_PROVISIONS
            known_ea_ids = {
                "EA-S95-KETs",
                "EA-S88A-payslip",
                "EA-S10-notice",
                "EA-PART-IV-hours",
                "EA-PART-X-annual-leave",
                "EA-S89-sick-leave",
            }
            for pid in result:
                assert pid in known_ea_ids, f"Fallback provision '{pid}' not in known EA provisions"

    def test_fallback_cpf_provisions(self):
        """Fallback for CPF domain should include CPFA-S52."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            result = _lookup_provisions(["cpf"], query="contribution")
            assert "CPFA-S52" in result

    def test_fallback_wsh_provisions(self):
        """Fallback for WSH domain should include WSH-related provisions."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            result = _lookup_provisions(["wsh"], query="safety")
            assert any("WSH" in pid or "WICA" in pid or "WSHA" in pid for pid in result)

    def test_converts_db_ids_to_strings(self):
        """Provision IDs from the database (integers) must be converted to strings."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 123}, {"id": 456}]
            result = _lookup_provisions(["employment_act"], query="overtime")
            for pid in result:
                assert isinstance(pid, str), f"Provision ID {pid!r} should be a string"

    def test_respects_limit(self):
        """Should pass a limit to search_provisions."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["employment_act"], query="test")
            call_kwargs = mock_search.call_args
            limit_arg = call_kwargs.kwargs.get("limit")
            assert limit_arg is not None and limit_arg > 0

    def test_query_parameter_required(self):
        """The query parameter should be accepted and used."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 1}]
            _lookup_provisions(["employment_act"], query="annual leave days")
            call_kwargs = mock_search.call_args
            query_arg = call_kwargs.kwargs.get("query") or call_kwargs.args[0]
            assert "annual leave" in query_arg.lower()

    def test_empty_domains_returns_empty(self):
        """Empty domain list should return an empty provision list."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        result = _lookup_provisions([], query="anything")
        assert result == []


class TestGenerateGroundedResponse:
    """Tests for _generate_grounded_response — query-specific KB-grounded responses."""

    def test_returns_string(self):
        """Must always return a string response."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="What is the notice period?",
            domains=["employment_act"],
            provisions=[],
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_different_queries_same_domain_produce_different_responses(self):
        """Two different queries within the same domain must produce
        different response text. This is the core requirement —
        the stub returns identical text per domain regardless of query."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        response_a = _generate_grounded_response(
            query="How many days of annual leave must I give?",
            domains=["employment_act"],
            provisions=[
                {
                    "provision_id": "EA-PART-X-annual-leave",
                    "title": "Employment Act Part X - Annual Leave",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        response_b = _generate_grounded_response(
            query="What is the notice period for termination?",
            domains=["employment_act"],
            provisions=[
                {
                    "provision_id": "EA-S10-notice",
                    "title": "Employment Act s10 - Notice of Termination",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        assert response_a != response_b, (
            "Different queries with different provisions should produce different responses. "
            "Got identical responses, indicating the function is still a stub."
        )

    def test_response_mentions_provision_titles(self):
        """Response should reference the provision titles that were cited."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        provisions = [
            {
                "provision_id": "EA-PART-X-annual-leave",
                "title": "Employment Act Part X - Annual Leave",
                "authority_level": "statutory",
                "status": "valid",
            }
        ]
        result = _generate_grounded_response(
            query="How many days of annual leave?",
            domains=["employment_act"],
            provisions=provisions,
        )
        # The response should mention the provision title
        assert "Annual Leave" in result or "annual leave" in result.lower()

    def test_response_addresses_query_topic(self):
        """Response should address the topic of the query, not be generic."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="What CPF contribution rate applies to a 58-year-old?",
            domains=["cpf"],
            provisions=[
                {
                    "provision_id": "CPFA-S52",
                    "title": "CPF Act s52 - Late Payment Interest",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        # Should mention CPF or contribution, addressing the query
        result_lower = result.lower()
        assert "cpf" in result_lower or "contribution" in result_lower

    def test_empty_provisions_still_generates_response(self):
        """Even without provisions, should generate a domain-relevant response."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="What are the overtime rules?",
            domains=["employment_act"],
            provisions=[],
        )
        assert len(result) > 0
        assert isinstance(result, str)

    def test_multiple_domains_covered(self):
        """Response should address multiple domains when provided."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="What are my obligations for foreign workers regarding CPF?",
            domains=["foreign_manpower", "cpf"],
            provisions=[
                {
                    "provision_id": "EFMA-conditions",
                    "title": "EFMA - Work Pass Conditions",
                    "authority_level": "statutory",
                    "status": "valid",
                },
                {
                    "provision_id": "CPFA-S52",
                    "title": "CPF Act s52 - Late Payment Interest",
                    "authority_level": "statutory",
                    "status": "valid",
                },
            ],
        )
        result_lower = result.lower()
        # Should reference content from at least one of the domains
        has_fm = "foreign" in result_lower or "work pass" in result_lower or "efma" in result_lower
        has_cpf = "cpf" in result_lower or "contribution" in result_lower
        assert has_fm or has_cpf, "Response should address at least one of the queried domains"

    def test_provision_citation_section_appended(self):
        """When provisions are provided, their titles should be referenced."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        provisions = [
            {
                "provision_id": "EA-S10-notice",
                "title": "Employment Act s10 - Notice of Termination",
                "authority_level": "statutory",
                "status": "valid",
            }
        ]
        result = _generate_grounded_response(
            query="What is the notice period?",
            domains=["employment_act"],
            provisions=provisions,
        )
        # Should contain the provision reference somewhere
        assert "provision" in result.lower() or "Employment Act" in result

    def test_wsh_query_mentions_safety(self):
        """A WSH query should produce a response mentioning workplace safety."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="What are the incident reporting requirements?",
            domains=["wsh"],
            provisions=[
                {
                    "provision_id": "WSH-incident-reporting",
                    "title": "WSH (Incident Reporting) Regulations",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        result_lower = result.lower()
        assert (
            "safety" in result_lower
            or "incident" in result_lower
            or "wsh" in result_lower
            or "reporting" in result_lower
        )


class TestHelperFunctions:
    """Tests for the helper functions used by _generate_grounded_response."""

    def test_get_provision_details_returns_list(self):
        """_get_provision_details must return a list of dicts."""
        from hr_advisory.api.routers.advisory import _get_provision_details

        provisions = [
            {
                "provision_id": "EA-S10-notice",
                "title": "Employment Act s10 - Notice of Termination",
            }
        ]
        result = _get_provision_details(provisions)
        assert isinstance(result, list)

    def test_get_provision_details_uses_kb_data(self):
        """Should attempt to retrieve full provision data from the KB."""
        from hr_advisory.api.routers.advisory import _get_provision_details

        provisions = [
            {
                "provision_id": "EA-S10-notice",
                "title": "Employment Act s10 - Notice of Termination",
            }
        ]
        result = _get_provision_details(provisions)
        # Each detail should at minimum have the title
        for detail in result:
            assert "title" in detail

    def test_generate_topic_intro_returns_string_or_none(self):
        """_generate_topic_intro returns a string intro or empty string."""
        from hr_advisory.api.routers.advisory import _generate_topic_intro

        result = _generate_topic_intro("annual leave entitlement", ["employment_act"])
        assert isinstance(result, str)

    def test_generate_topic_intro_query_specific(self):
        """Different queries should produce different topic intros."""
        from hr_advisory.api.routers.advisory import _generate_topic_intro

        intro_a = _generate_topic_intro("annual leave entitlement", ["employment_act"])
        intro_b = _generate_topic_intro("cpf contribution rates", ["cpf"])
        # At least one should be non-empty, and they should differ
        if intro_a and intro_b:
            assert intro_a != intro_b

    def test_get_domain_context_returns_list(self):
        """_get_domain_context must return a list of strings."""
        from hr_advisory.api.routers.advisory import _get_domain_context

        result = _get_domain_context("overtime rules", ["employment_act"])
        assert isinstance(result, list)

    def test_get_domain_context_not_empty_for_known_domain(self):
        """Known domains should produce at least some context."""
        from hr_advisory.api.routers.advisory import _get_domain_context

        result = _get_domain_context("overtime", ["employment_act"])
        assert len(result) > 0

    def test_get_domain_context_query_specific(self):
        """Different queries within the same domain should produce
        different context strings."""
        from hr_advisory.api.routers.advisory import _get_domain_context

        context_a = _get_domain_context("annual leave", ["employment_act"])
        context_b = _get_domain_context("notice period termination", ["employment_act"])
        # Should produce non-empty and different results
        if context_a and context_b:
            assert context_a != context_b, (
                "Different queries should produce different domain context"
            )


class TestCallSiteIntegration:
    """Tests that call sites pass the query parameter to _lookup_provisions."""

    def test_lookup_provisions_accepts_query_parameter(self):
        """_lookup_provisions must accept a 'query' keyword argument."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        import inspect

        sig = inspect.signature(_lookup_provisions)
        assert "query" in sig.parameters, (
            "_lookup_provisions must have a 'query' parameter"
        )

    def test_lookup_provisions_query_has_default(self):
        """The query parameter should have a default value (for backwards compat)."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        import inspect

        sig = inspect.signature(_lookup_provisions)
        param = sig.parameters["query"]
        assert param.default != inspect.Parameter.empty, (
            "query parameter should have a default value for backwards compatibility"
        )
