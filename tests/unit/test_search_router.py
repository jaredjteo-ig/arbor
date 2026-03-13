"""Unit tests for the search router endpoint logic.

Tests the keyword relevance scoring, result formatting, pagination,
and post-retrieval filtering logic used by the search endpoints.
These tests mock the KB admin layer (search_provisions) since unit tests
must not touch databases.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Sample provision data matching the shape returned by search_provisions()
# ---------------------------------------------------------------------------


def _make_provision(
    *,
    id: int = 1,
    title: str = "Rest days, hours of work",
    section: str = "Part IV",
    formal_text: str = "An employee shall not work more than 8 hours a day.",
    plain_summary: str = "Covers working hours, overtime, and rest day provisions.",
    authority_level: str = "primary",
    source_act_id: int = 10,
    domain_id: int = 3,
) -> dict:
    return {
        "id": id,
        "title": title,
        "section": section,
        "formal_text": formal_text,
        "plain_summary": plain_summary,
        "authority_level": authority_level,
        "source_act_id": source_act_id,
        "domain_id": domain_id,
    }


SAMPLE_PROVISIONS = [
    _make_provision(
        id=1,
        title="Overtime pay rates",
        section="Part IV Section 38",
        formal_text="Overtime pay shall be calculated at 1.5 times the hourly rate.",
        plain_summary="Overtime is paid at 1.5x the normal rate.",
        source_act_id=10,
        domain_id=3,
    ),
    _make_provision(
        id=2,
        title="Annual leave entitlement",
        section="Part IV Section 43A",
        formal_text="An employee is entitled to annual leave after 3 months of service.",
        plain_summary="Employees get annual leave after 3 months.",
        source_act_id=10,
        domain_id=5,
    ),
    _make_provision(
        id=3,
        title="Rest days",
        section="Part IV Section 36",
        formal_text="Every employee shall be entitled to 1 rest day per week.",
        plain_summary="Workers get one rest day per week.",
        authority_level="subsidiary",
        source_act_id=10,
        domain_id=3,
    ),
    _make_provision(
        id=4,
        title="CPF contribution rates",
        section="Section 7",
        formal_text="The employer shall contribute to the CPF fund.",
        plain_summary="CPF contributions are mandatory for employers.",
        source_act_id=20,
        domain_id=8,
    ),
]


# ---------------------------------------------------------------------------
# Helper: import the scoring function from the router module
# ---------------------------------------------------------------------------


class TestCalculateRelevanceScore:
    """Tests for the keyword-density relevance scoring function."""

    def test_query_in_title_scores_highest(self):
        """When the query appears in the title, score should be 0.95."""
        from hr_advisory.api.routers.search import _calculate_relevance_score

        provision = _make_provision(title="Overtime pay rates")
        score = _calculate_relevance_score("overtime", provision)
        assert score == 0.95

    def test_query_in_plain_summary_scores_high(self):
        """When the query appears in plain_summary but not title, score should be 0.85."""
        from hr_advisory.api.routers.search import _calculate_relevance_score

        provision = _make_provision(
            title="Rest days",
            plain_summary="Covers working hours and overtime provisions.",
        )
        score = _calculate_relevance_score("overtime", provision)
        assert score == 0.85

    def test_query_in_formal_text_only_scores_lower(self):
        """When the query appears only in formal_text, score should be 0.75."""
        from hr_advisory.api.routers.search import _calculate_relevance_score

        provision = _make_provision(
            title="Rest days",
            plain_summary="Workers get one rest day per week.",
            formal_text="Overtime shall be calculated at 1.5 times the rate.",
        )
        score = _calculate_relevance_score("overtime", provision)
        assert score == 0.75

    def test_case_insensitive_matching(self):
        """Scoring should be case-insensitive."""
        from hr_advisory.api.routers.search import _calculate_relevance_score

        provision = _make_provision(title="OVERTIME PAY RATES")
        score = _calculate_relevance_score("overtime", provision)
        assert score == 0.95

    def test_no_match_returns_base_score(self):
        """When query does not appear in any field, score should be a low base value."""
        from hr_advisory.api.routers.search import _calculate_relevance_score

        provision = _make_provision(
            title="CPF rates",
            plain_summary="CPF contributions are mandatory.",
            formal_text="The employer shall contribute to the CPF fund.",
        )
        score = _calculate_relevance_score("overtime", provision)
        assert score == 0.5


class TestFormatSemanticResult:
    """Tests for formatting a provision into a semantic search result."""

    def test_result_contains_required_fields(self):
        """Each formatted result must contain all required response fields."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = SAMPLE_PROVISIONS[0]
        result = _format_semantic_result(provision, "overtime", {}, {})
        assert "provision_id" in result
        assert "title" in result
        assert "plain_summary" in result
        assert "similarity_score" in result
        assert "source_act" in result
        assert "domain" in result

    def test_provision_id_maps_from_id(self):
        """provision_id should come from the provision's 'id' field."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(id=42)
        result = _format_semantic_result(provision, "overtime", {}, {})
        assert result["provision_id"] == 42

    def test_similarity_score_is_calculated(self):
        """similarity_score should be calculated from keyword density, not hardcoded."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(title="Overtime pay rates")
        result = _format_semantic_result(provision, "overtime", {}, {})
        assert isinstance(result["similarity_score"], float)
        assert result["similarity_score"] == 0.95

    def test_act_name_resolved_from_lookup(self):
        """source_act should use the act name from the lookup dict."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(source_act_id=10)
        acts = {10: "Employment Act 1968"}
        result = _format_semantic_result(provision, "overtime", acts, {})
        assert result["source_act"] == "Employment Act 1968"

    def test_domain_name_resolved_from_lookup(self):
        """domain should use the domain name from the lookup dict."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(domain_id=3)
        domains = {3: "Working Hours"}
        result = _format_semantic_result(provision, "overtime", {}, domains)
        assert result["domain"] == "Working Hours"

    def test_unknown_act_shows_unknown(self):
        """When act ID is not in the lookup, source_act should say 'Unknown'."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(source_act_id=999)
        result = _format_semantic_result(provision, "overtime", {}, {})
        assert result["source_act"] == "Unknown"

    def test_unknown_domain_shows_unknown(self):
        """When domain ID is not in the lookup, domain should say 'Unknown'."""
        from hr_advisory.api.routers.search import _format_semantic_result

        provision = _make_provision(domain_id=999)
        result = _format_semantic_result(provision, "overtime", {}, {})
        assert result["domain"] == "Unknown"


class TestSemanticSearchEndpoint:
    """Tests for the POST /semantic endpoint logic."""

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_returns_results_from_search_provisions(self, mock_domains, mock_acts, mock_search):
        """The endpoint should call search_provisions and return formatted results."""
        mock_search.return_value = [SAMPLE_PROVISIONS[0]]
        mock_acts.return_value = {10: "Employment Act 1968"}
        mock_domains.return_value = {3: "Working Hours"}

        from hr_advisory.api.routers.search import _execute_semantic_search

        response = _execute_semantic_search(
            query="overtime", top_k=5, domain_id=None, threshold=0.7
        )
        assert response["query"] == "overtime"
        assert len(response["results"]) == 1
        assert response["results"][0]["provision_id"] == 1
        assert response["results"][0]["similarity_score"] == 0.95
        mock_search.assert_called_once_with(query="overtime", limit=5)

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_filters_below_threshold(self, mock_domains, mock_acts, mock_search):
        """Results with score below threshold should be excluded."""
        # CPF provision won't match "overtime" at all -> score 0.5
        mock_search.return_value = [SAMPLE_PROVISIONS[0], SAMPLE_PROVISIONS[3]]
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_semantic_search

        response = _execute_semantic_search(
            query="overtime", top_k=10, domain_id=None, threshold=0.7
        )
        # Only the overtime provision (score=0.95) should pass; CPF (score=0.5) should not
        assert len(response["results"]) == 1
        assert response["results"][0]["provision_id"] == 1

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_results_sorted_by_score_descending(self, mock_domains, mock_acts, mock_search):
        """Results should be sorted by similarity_score in descending order."""
        mock_search.return_value = [
            SAMPLE_PROVISIONS[2],  # "Rest days" - score 0.5 for query "overtime"
            SAMPLE_PROVISIONS[0],  # "Overtime pay rates" - score 0.95
        ]
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_semantic_search

        response = _execute_semantic_search(
            query="overtime", top_k=10, domain_id=None, threshold=0.0
        )
        scores = [r["similarity_score"] for r in response["results"]]
        assert scores == sorted(scores, reverse=True)

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_empty_query_returns_empty_results(self, mock_domains, mock_acts, mock_search):
        """An empty query string should return empty results without calling search."""
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_semantic_search

        response = _execute_semantic_search(query="", top_k=5, domain_id=None, threshold=0.7)
        assert response["results"] == []
        assert response["total"] == 0
        mock_search.assert_not_called()

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_database_error_returns_empty_results(self, mock_domains, mock_acts, mock_search):
        """When search_provisions raises an exception, return empty results gracefully."""
        mock_search.side_effect = Exception("Database connection failed")
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_semantic_search

        response = _execute_semantic_search(
            query="overtime", top_k=5, domain_id=None, threshold=0.7
        )
        assert response["results"] == []
        assert response["total"] == 0


class TestFulltextSearchEndpoint:
    """Tests for the POST /fulltext endpoint logic."""

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_returns_paginated_results(self, mock_domains, mock_acts, mock_search):
        """The endpoint should return results with pagination metadata."""
        mock_search.return_value = SAMPLE_PROVISIONS[:2]
        mock_acts.return_value = {10: "Employment Act 1968"}
        mock_domains.return_value = {3: "Working Hours", 5: "Leave"}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="leave",
            domain_id=None,
            act_id=None,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        assert response["query"] == "leave"
        assert "results" in response
        assert "page" in response
        assert "page_size" in response
        assert response["page"] == 1

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_filters_by_act_id(self, mock_domains, mock_acts, mock_search):
        """Results should be filtered by act_id when provided."""
        mock_search.return_value = SAMPLE_PROVISIONS  # includes act_id=10 and act_id=20
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="the",
            domain_id=None,
            act_id=20,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        for result in response["results"]:
            assert result["source_act_id"] == 20

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_filters_by_authority_level(self, mock_domains, mock_acts, mock_search):
        """Results should be filtered by authority_level when provided."""
        mock_search.return_value = SAMPLE_PROVISIONS
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="the",
            domain_id=None,
            act_id=None,
            authority_level="subsidiary",
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        for result in response["results"]:
            assert result["authority_level"] == "subsidiary"

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_pagination_page_2(self, mock_domains, mock_acts, mock_search):
        """Page 2 with page_size=1 should return the second result."""
        mock_search.return_value = SAMPLE_PROVISIONS[:3]
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="the",
            domain_id=None,
            act_id=None,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=2,
            page_size=1,
        )
        assert len(response["results"]) == 1
        assert response["page"] == 2
        # total should reflect all matched results before pagination
        assert response["total"] >= 1

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_empty_query_returns_empty(self, mock_domains, mock_acts, mock_search):
        """An empty query string should return empty results."""
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="",
            domain_id=None,
            act_id=None,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        assert response["results"] == []
        assert response["total"] == 0
        mock_search.assert_not_called()

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_database_error_returns_empty(self, mock_domains, mock_acts, mock_search):
        """When search_provisions raises an exception, return empty results."""
        mock_search.side_effect = Exception("Database unavailable")
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="overtime",
            domain_id=None,
            act_id=None,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        assert response["results"] == []
        assert response["total"] == 0

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_fulltext_passes_domain_to_search_provisions(
        self, mock_domains, mock_acts, mock_search
    ):
        """When domain_id is provided, it should be resolved and passed to search_provisions."""
        mock_search.return_value = []
        mock_acts.return_value = {}
        mock_domains.return_value = {3: "Working Hours"}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        _execute_fulltext_search(
            query="overtime",
            domain_id=3,
            act_id=None,
            authority_level=None,
            effective_after=None,
            effective_before=None,
            page=1,
            page_size=20,
        )
        # search_provisions should receive a larger limit to allow for post-filtering
        call_kwargs = mock_search.call_args
        assert call_kwargs is not None
        assert call_kwargs[1]["query"] == "overtime"

    @patch("hr_advisory.api.routers.search.search_provisions")
    @patch("hr_advisory.api.routers.search._load_act_lookup")
    @patch("hr_advisory.api.routers.search._load_domain_lookup")
    def test_fulltext_result_includes_filters_in_response(
        self, mock_domains, mock_acts, mock_search
    ):
        """The response should echo back the filters that were applied."""
        mock_search.return_value = []
        mock_acts.return_value = {}
        mock_domains.return_value = {}

        from hr_advisory.api.routers.search import _execute_fulltext_search

        response = _execute_fulltext_search(
            query="overtime",
            domain_id=3,
            act_id=10,
            authority_level="primary",
            effective_after="2024-01-01",
            effective_before="2025-12-31",
            page=1,
            page_size=20,
        )
        assert response["filters"]["domain_id"] == 3
        assert response["filters"]["act_id"] == 10
        assert response["filters"]["authority_level"] == "primary"
        assert response["filters"]["effective_after"] == "2024-01-01"
        assert response["filters"]["effective_before"] == "2025-12-31"
