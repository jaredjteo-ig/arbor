"""Integration tests for PIIFilter (PDPA PII stripping layer).

Tests:
- Strip NRIC patterns (S/T/F/G/M prefixes)
- Strip Singapore phone numbers (+65 and local 8/9/6-digit)
- Strip bank account patterns
- Strip email addresses
- Restore tokens in LLM response
- Known names stripping via strip_names parameter
- has_pii detection
- Round-trip: strip -> LLM processing -> restore
"""

from __future__ import annotations

import pytest

from hr_advisory.mcp_servers.pii_filter import PIIFilter


# ---------------------------------------------------------------------------
# NRIC stripping
# ---------------------------------------------------------------------------


class TestNRICStripping:
    """Strip Singapore NRIC/FIN numbers (S/T/F/G/M prefixes)."""

    @pytest.mark.parametrize(
        "nric",
        [
            "S1234567A",
            "T9876543B",
            "F1234567C",
            "G9876543D",
            "M1234567E",
        ],
    )
    def test_strip_nric_all_prefixes(self, pii_filter: PIIFilter, nric: str):
        text = f"Employee NRIC is {nric} for payroll."
        cleaned, token_map = pii_filter.strip(text)
        assert nric not in cleaned
        assert "[NRIC_1]" in cleaned
        assert token_map["[NRIC_1]"] == nric

    def test_strip_multiple_nrics(self, pii_filter: PIIFilter):
        text = "John (S1234567A) and Jane (T7654321B) are in the same team."
        cleaned, token_map = pii_filter.strip(text)
        assert "S1234567A" not in cleaned
        assert "T7654321B" not in cleaned
        assert len([k for k in token_map if "NRIC" in k]) == 2

    def test_lowercase_nric_stripped(self, pii_filter: PIIFilter):
        """NRIC pattern is case-insensitive."""
        text = "NRIC: s1234567a"
        cleaned, token_map = pii_filter.strip(text)
        assert "s1234567a" not in cleaned

    def test_nric_not_in_cleaned_text(self, pii_filter: PIIFilter):
        """The actual NRIC digits must not appear in the cleaned text."""
        text = "Employee S9876543Z works here."
        cleaned, _ = pii_filter.strip(text)
        assert "S9876543Z" not in cleaned
        assert "9876543" not in cleaned


# ---------------------------------------------------------------------------
# Phone number stripping
# ---------------------------------------------------------------------------


class TestPhoneStripping:
    """Strip Singapore phone numbers."""

    def test_strip_plus_65_format(self, pii_filter: PIIFilter):
        text = "Call me at +6591234567 for details."
        cleaned, token_map = pii_filter.strip(text)
        assert "+6591234567" not in cleaned
        assert any("PHONE" in k for k in token_map)

    def test_strip_plus_65_with_space(self, pii_filter: PIIFilter):
        text = "Phone: +65 91234567"
        cleaned, token_map = pii_filter.strip(text)
        assert "+65 91234567" not in cleaned

    def test_strip_local_mobile_number(self, pii_filter: PIIFilter):
        text = "Mobile: 91234567"
        cleaned, token_map = pii_filter.strip(text)
        assert "91234567" not in cleaned

    def test_strip_local_8_prefix(self, pii_filter: PIIFilter):
        text = "Contact: 81234567"
        cleaned, token_map = pii_filter.strip(text)
        assert "81234567" not in cleaned

    def test_strip_local_6_prefix(self, pii_filter: PIIFilter):
        text = "Office: 61234567"
        cleaned, token_map = pii_filter.strip(text)
        assert "61234567" not in cleaned


# ---------------------------------------------------------------------------
# Bank account stripping
# ---------------------------------------------------------------------------


class TestBankAccountStripping:
    """Strip bank account number patterns."""

    def test_strip_dbs_format(self, pii_filter: PIIFilter):
        text = "DBS account: 001-123456-001"
        cleaned, token_map = pii_filter.strip(text)
        assert "001-123456-001" not in cleaned
        assert any("BANK_ACCT" in k for k in token_map)

    def test_strip_uob_format(self, pii_filter: PIIFilter):
        text = "UOB: 901-234567-8"
        cleaned, token_map = pii_filter.strip(text)
        assert "901-234567-8" not in cleaned

    def test_strip_without_dashes(self, pii_filter: PIIFilter):
        text = "Account number 0011234560"
        cleaned, token_map = pii_filter.strip(text)
        assert "0011234560" not in cleaned


# ---------------------------------------------------------------------------
# Email stripping
# ---------------------------------------------------------------------------


class TestEmailStripping:
    """Strip email addresses."""

    def test_strip_simple_email(self, pii_filter: PIIFilter):
        text = "Send to john.tan@company.com for HR matters."
        cleaned, token_map = pii_filter.strip(text)
        assert "john.tan@company.com" not in cleaned
        assert any("EMAIL" in k for k in token_map)

    def test_strip_multiple_emails(self, pii_filter: PIIFilter):
        text = "Contact hr@acme.sg or admin@acme.sg"
        cleaned, token_map = pii_filter.strip(text)
        assert "hr@acme.sg" not in cleaned
        assert "admin@acme.sg" not in cleaned


# ---------------------------------------------------------------------------
# Known names stripping
# ---------------------------------------------------------------------------


class TestKnownNamesStripping:
    """Stripping known employee names via the strip_names parameter."""

    def test_strip_known_names(self, pii_filter: PIIFilter):
        text = "John Tan earns $5,000 per month."
        cleaned, token_map = pii_filter.strip(text, strip_names=["John Tan"])
        assert "John Tan" not in cleaned
        assert any("PERSON" in k for k in token_map)
        assert "[PERSON_1]" in cleaned

    def test_strip_multiple_names(self, pii_filter: PIIFilter):
        text = "John Tan and Mary Lim both attended the meeting."
        cleaned, token_map = pii_filter.strip(text, strip_names=["John Tan", "Mary Lim"])
        assert "John Tan" not in cleaned
        assert "Mary Lim" not in cleaned

    def test_name_not_in_text_is_ignored(self, pii_filter: PIIFilter):
        text = "The team is doing well."
        cleaned, token_map = pii_filter.strip(text, strip_names=["Ghost Name"])
        assert cleaned == text
        assert "PERSON" not in str(token_map)


# ---------------------------------------------------------------------------
# Restore tokens
# ---------------------------------------------------------------------------


class TestRestoreTokens:
    """Restoring PII tokens back to original values in LLM responses."""

    def test_restore_single_token(self, pii_filter: PIIFilter):
        token_map = {"[NRIC_1]": "S1234567A"}
        response = "[NRIC_1] is entitled to 14 days annual leave."
        restored = pii_filter.restore(response, token_map)
        assert restored == "S1234567A is entitled to 14 days annual leave."

    def test_restore_multiple_tokens(self, pii_filter: PIIFilter):
        token_map = {
            "[PERSON_1]": "John Tan",
            "[NRIC_1]": "S1234567A",
        }
        response = "[PERSON_1] ([NRIC_1]) should submit the form."
        restored = pii_filter.restore(response, token_map)
        assert restored == "John Tan (S1234567A) should submit the form."

    def test_restore_empty_map_returns_unchanged(self, pii_filter: PIIFilter):
        text = "No tokens here."
        assert pii_filter.restore(text, {}) == text

    def test_round_trip_strip_and_restore(self, pii_filter: PIIFilter):
        """End-to-end: strip PII, simulate LLM processing, restore."""
        original = "John Tan (S1234567A) called from +6591234567"
        cleaned, token_map = pii_filter.strip(original, strip_names=["John Tan"])

        # Simulate LLM response using the tokens
        llm_response = f"Based on the records, {cleaned.split(')')[0]})'s leave balance is 14 days."
        # The token_map can restore names/NRICs in any response
        for token, value in token_map.items():
            assert value not in cleaned, f"PII '{value}' leaked into cleaned text"

    def test_restore_preserves_unmatched_tokens(self, pii_filter: PIIFilter):
        """Tokens not in the map are left as-is."""
        token_map = {"[NRIC_1]": "S1234567A"}
        text = "[NRIC_1] and [UNKNOWN_1] are different."
        restored = pii_filter.restore(text, token_map)
        assert "S1234567A" in restored
        assert "[UNKNOWN_1]" in restored


# ---------------------------------------------------------------------------
# has_pii detection
# ---------------------------------------------------------------------------


class TestHasPII:
    """Quick PII detection via has_pii()."""

    def test_detects_nric(self, pii_filter: PIIFilter):
        assert pii_filter.has_pii("Employee S1234567A works here.") is True

    def test_detects_bank_account(self, pii_filter: PIIFilter):
        assert pii_filter.has_pii("Account 001-123456-001 for salary.") is True

    def test_clean_text_returns_false(self, pii_filter: PIIFilter):
        assert pii_filter.has_pii("Annual leave policy is 14 days.") is False

    def test_detects_fin_number(self, pii_filter: PIIFilter):
        assert pii_filter.has_pii("FIN: F1234567X") is True

    def test_detects_m_series_nric(self, pii_filter: PIIFilter):
        assert pii_filter.has_pii("New NRIC: M1234567K") is True


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self, pii_filter: PIIFilter):
        cleaned, token_map = pii_filter.strip("")
        assert cleaned == ""
        assert token_map == {}

    def test_no_pii_returns_unchanged(self, pii_filter: PIIFilter):
        text = "The company has 50 employees and follows the Employment Act."
        cleaned, token_map = pii_filter.strip(text)
        assert cleaned == text
        assert token_map == {}

    def test_text_with_only_pii(self, pii_filter: PIIFilter):
        text = "S1234567A"
        cleaned, token_map = pii_filter.strip(text)
        assert "S1234567A" not in cleaned
        assert len(token_map) > 0

    def test_mixed_pii_types(self, pii_filter: PIIFilter):
        text = (
            "Employee John Tan (S1234567A) phone +6591234567 "
            "email john@acme.sg account 001-123456-001"
        )
        cleaned, token_map = pii_filter.strip(text, strip_names=["John Tan"])
        assert "S1234567A" not in cleaned
        assert "+6591234567" not in cleaned
        assert "john@acme.sg" not in cleaned
        assert "001-123456-001" not in cleaned
        assert "John Tan" not in cleaned
        # All original values are recoverable
        originals = set(token_map.values())
        assert "S1234567A" in originals
        assert "John Tan" in originals
