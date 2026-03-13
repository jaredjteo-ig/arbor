"""Unit tests for advisory safety chain — stub replacement validation.

Validates that the safety chain's KB lookup and response generation
stages produce query-specific outputs rather than hardcoded/static data.

Tier 1 (Unit): Tests the advisory pipeline functions in isolation.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


class TestSafetyChainLookupNotStatic:
    """Verify _lookup_provisions is no longer a static dict lookup."""

    def test_lookup_calls_search_provisions(self):
        """_lookup_provisions must call search_provisions, not use hardcoded dict."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = [{"id": 100}]
            _lookup_provisions(["employment_act"], query="annual leave")
            mock_search.assert_called_once()

    def test_lookup_uses_query_for_search(self):
        """The query text must be forwarded to the search function."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []
            _lookup_provisions(["employment_act"], query="sick leave entitlement")
            call_args = mock_search.call_args
            query_arg = call_args.kwargs.get("query") or call_args.args[0]
            assert "sick leave" in query_arg.lower()

    def test_different_queries_produce_different_search_calls(self):
        """Two different queries should trigger different search calls."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        with patch("hr_advisory.api.routers.advisory.search_provisions") as mock_search:
            mock_search.return_value = []

            _lookup_provisions(["employment_act"], query="overtime pay")
            first_query = mock_search.call_args.kwargs.get("query") or mock_search.call_args.args[0]

            mock_search.reset_mock()

            _lookup_provisions(["employment_act"], query="termination notice")
            second_query = (
                mock_search.call_args.kwargs.get("query") or mock_search.call_args.args[0]
            )

            assert first_query != second_query


class TestSafetyChainResponseNotStatic:
    """Verify _generate_grounded_response is no longer a static dict lookup."""

    def test_annual_leave_query_mentions_leave(self):
        """An annual leave query must produce response mentioning leave."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
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
        assert "leave" in result.lower()

    def test_cpf_query_mentions_cpf(self):
        """A CPF query must produce response mentioning CPF specifics."""
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
        assert "cpf" in result.lower()

    def test_two_ea_queries_differ(self):
        """Two EA queries about different topics must produce different text."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        r1 = _generate_grounded_response(
            query="What are the payslip requirements?",
            domains=["employment_act"],
            provisions=[
                {
                    "provision_id": "EA-S88A-payslip",
                    "title": "Employment Act s88A - Itemised Payslips",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        r2 = _generate_grounded_response(
            query="How do rest days work under the Employment Act?",
            domains=["employment_act"],
            provisions=[
                {
                    "provision_id": "EA-PART-IV-hours",
                    "title": "Employment Act Part IV - Hours of Work and Overtime",
                    "authority_level": "statutory",
                    "status": "valid",
                }
            ],
        )
        assert r1 != r2, "Responses for 'payslip requirements' and 'rest days' should differ"

    def test_response_not_identical_to_old_stub(self):
        """Response must not be the exact old hardcoded EA stub text."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        old_stub = (
            "Based on the Employment Act, all employees under a contract of service "
            "are covered. Key provisions include: mandatory Key Employment Terms (KETs) "
            "under s95A, itemised payslips under s88A, and notice period requirements "
            "under s10. Part IV covers rest days, working hours, and overtime for "
            "employees earning up to $4,500/month."
        )
        result = _generate_grounded_response(
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
        assert (
            result != old_stub
        ), "Response is still the old hardcoded stub text — must be query-specific"

    def test_response_with_no_provisions_not_empty(self):
        """Even without provisions, the function must return non-empty text."""
        from hr_advisory.api.routers.advisory import _generate_grounded_response

        result = _generate_grounded_response(
            query="Tell me about workplace safety requirements",
            domains=["wsh"],
            provisions=[],
        )
        assert len(result) > 20, "Response should be substantive, not empty or trivially short"


class TestPlatformHandlerCallSite:
    """Verify that platform.py handler passes query to _lookup_provisions."""

    def test_platform_handler_imports_lookup_provisions(self):
        """platform.py must be able to import _lookup_provisions."""
        from hr_advisory.api.routers.advisory import _lookup_provisions

        assert callable(_lookup_provisions)

    def test_platform_handler_code_passes_query(self):
        """The advisory_query_handler in platform.py must pass query
        to _lookup_provisions. We verify by inspecting the source."""
        import inspect

        from hr_advisory.api.platform import _register_handlers

        source = inspect.getsource(_register_handlers)
        # The handler should call _lookup_provisions with the query
        assert "_lookup_provisions(domains" in source
        # And it should pass the clean_query as the query parameter
        assert "clean_query" in source or "query" in source
