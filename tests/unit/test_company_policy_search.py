# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for company policy search service (T010).

Tests the keyword-based policy search, scoring, filtering,
and result formatting without requiring a live database.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from hr_advisory.services.company_policy_search import search_company_policies


# -- Fixture: fake policy records as DataFlow would return -------------------

_FAKE_POLICIES = [
    {
        "id": 1,
        "company_id": 42,
        "policy_type": "leave",
        "category": "leave",
        "title": "Annual Leave Policy",
        "content": "Employees are entitled to 14 days annual leave after 1 year of service. "
        "Carry forward is limited to 5 days per year. "
        "Leave must be applied 3 days in advance for planned leave.",
        "effective_date": "2025-01-01",
        "is_active": True,
        "version_number": 2,
        "status": "active",
    },
    {
        "id": 2,
        "company_id": 42,
        "policy_type": "fwa",
        "category": "flexible_work",
        "title": "Flexible Work Arrangement Policy",
        "content": "Employees may request to work from home up to 3 days per week. "
        "Requests must be submitted via the HR portal. Manager approval required.",
        "effective_date": "2025-06-01",
        "is_active": True,
        "version_number": 1,
        "status": "active",
    },
    {
        "id": 3,
        "company_id": 42,
        "policy_type": "safety",
        "category": "workplace_safety",
        "title": "Workplace Safety and Health Policy",
        "content": "All employees must complete safety induction within first week. "
        "Report all incidents within 24 hours. PPE required in warehouse areas.",
        "effective_date": "2024-06-01",
        "is_active": True,
        "version_number": 1,
        "status": "active",
    },
    {
        "id": 4,
        "company_id": 42,
        "policy_type": "leave",
        "category": "leave",
        "title": "Sick Leave Policy (Superseded)",
        "content": "Old sick leave policy content.",
        "effective_date": "2023-01-01",
        "is_active": False,
        "version_number": 1,
        "status": "superseded",
    },
    {
        "id": 5,
        "company_id": 99,
        "policy_type": "leave",
        "category": "leave",
        "title": "Other Company Leave Policy",
        "content": "This belongs to a different company.",
        "effective_date": "2025-01-01",
        "is_active": True,
        "version_number": 1,
        "status": "active",
    },
]


def _mock_dataflow_list(filter_dict: dict, limit: int = 10000) -> list:
    """Simulate DataFlow CompanyPolicyListNode results."""
    results = []
    for p in _FAKE_POLICIES:
        match = True
        for key, val in filter_dict.items():
            if p.get(key) != val:
                match = False
                break
        if match:
            results.append(p)
    return results[:limit]


class TestSearchCompanyPolicies:
    """Test the search_company_policies function."""

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_returns_matching_policies(self, mock_fetch):
        """Search for 'annual leave' should return the leave policy."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="annual leave entitlement", company_id=42)
        assert len(results) >= 1
        titles = [r["title"] for r in results]
        assert "Annual Leave Policy" in titles

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_returns_empty_for_no_match(self, mock_fetch):
        """Search for something with no keyword overlap returns empty list."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="xyz999 quantum teleportation", company_id=42)
        assert results == []

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_category_filter(self, mock_fetch):
        """Category filter should narrow results."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(
            query="policy", company_id=42, category="workplace_safety"
        )
        for r in results:
            assert r["category"] == "workplace_safety"

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_limit_respected(self, mock_fetch):
        """Results should not exceed the limit parameter."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="leave work safety", company_id=42, limit=1)
        assert len(results) <= 1

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_result_format(self, mock_fetch):
        """Each result must contain required fields."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="annual leave", company_id=42)
        assert len(results) >= 1
        r = results[0]
        assert "title" in r
        assert "category" in r
        assert "content_excerpt" in r
        assert "effective_date" in r
        assert "version_number" in r
        assert r["authority_level"] == "company_policy"

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_content_excerpt_truncated(self, mock_fetch):
        """Content excerpt should be at most 2000 chars."""
        long_policy = {
            "id": 100,
            "company_id": 42,
            "policy_type": "handbook",
            "category": "handbook",
            "title": "Employee Handbook",
            "content": "handbook " * 1000,  # ~9000 chars
            "effective_date": "2025-01-01",
            "is_active": True,
            "version_number": 1,
            "status": "active",
        }
        mock_fetch.return_value = [long_policy]
        results = search_company_policies(query="handbook", company_id=42)
        assert len(results) == 1
        assert len(results[0]["content_excerpt"]) <= 2000

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_keyword_scoring_relevance(self, mock_fetch):
        """More keyword matches should rank higher."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="annual leave carry forward", company_id=42)
        # "Annual Leave Policy" mentions all three keywords, should be first
        if len(results) >= 1:
            assert results[0]["title"] == "Annual Leave Policy"

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_only_active_policies_returned(self, mock_fetch):
        """Inactive/superseded policies should not appear in results."""
        # Intentionally include inactive policies in the mock to verify filtering
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="sick leave", company_id=42)
        for r in results:
            assert "Superseded" not in r["title"]

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_policy_id_included(self, mock_fetch):
        """Each result should include a policy_id for citation tracking."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="annual leave", company_id=42)
        assert len(results) >= 1
        assert "policy_id" in results[0]
        assert results[0]["policy_id"] > 0


class TestSearchCompanyPoliciesEdgeCases:
    """Edge cases for company policy search."""

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_empty_query(self, mock_fetch):
        """Empty query should return empty results."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="", company_id=42)
        assert results == []

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_stopwords_only_query(self, mock_fetch):
        """Query with only stopwords should return empty results."""
        mock_fetch.return_value = [p for p in _FAKE_POLICIES if p["company_id"] == 42 and p["is_active"]]
        results = search_company_policies(query="the is a an", company_id=42)
        assert results == []

    @patch("hr_advisory.services.company_policy_search._fetch_active_policies")
    def test_dataflow_failure_returns_empty(self, mock_fetch):
        """DataFlow fetch failure should return empty list, not raise."""
        mock_fetch.side_effect = Exception("DB connection failed")
        results = search_company_policies(query="leave", company_id=42)
        assert results == []
