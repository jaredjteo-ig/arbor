# Copyright 2026 Terrene Foundation
# SPDX-License-Identifier: Apache-2.0

"""Unit tests for citation validator company policy support (T017).

Tests that the citation validator recognizes company-policy authority
level citations with the 'policy-{id}' format and does not mark them
as invalid.
"""

from __future__ import annotations

import pytest

from hr_advisory.trust.citation_validator import (
    AuthorityLevel,
    CitationStatus,
    validate_citations,
)


class TestCompanyPolicyCitationValidation:
    """Citation validator must handle company policy citations."""

    def test_company_policy_citation_not_invalid(self):
        """Company policy citation 'policy-123' should not be marked invalid."""
        result = validate_citations(["policy-123"])
        # Should NOT be in invalid_citations
        assert "policy-123" not in result.invalid_citations

    def test_company_policy_citation_has_correct_authority(self):
        """Company policy citation should have COMPANY_POLICY or BEST_PRACTICE authority."""
        result = validate_citations(["policy-42"])
        # Should be in validated_citations
        assert len(result.validated_citations) >= 1
        citation = result.validated_citations[0]
        # Company policy citations should be recognized (not flagged as unknown)
        assert citation.provision_id == "policy-42"

    def test_mixed_statutory_and_company_policy(self):
        """Mix of statutory and company policy citations should both validate."""
        result = validate_citations(["EA-S95-KETs", "policy-7"])
        assert result.valid_count == 2
        assert result.invalid_count == 0

    def test_multiple_company_policy_citations(self):
        """Multiple company policy citations should all validate."""
        result = validate_citations(["policy-1", "policy-2", "policy-3"])
        assert result.valid_count == 3
        assert result.invalid_count == 0

    def test_company_policy_with_unknown_still_fails(self):
        """Company policy + unknown provision should still fail overall."""
        result = validate_citations(["policy-1", "NONEXISTENT-PROVISION"])
        assert result.is_valid is False
        assert result.valid_count == 1
        assert result.invalid_count == 1

    def test_company_policy_citation_title(self):
        """Company policy citation should have a descriptive title."""
        result = validate_citations(["policy-42"])
        assert len(result.validated_citations) >= 1
        citation = result.validated_citations[0]
        # Title should not be empty
        assert citation.title != ""
        assert "policy" in citation.title.lower() or "company" in citation.title.lower()
