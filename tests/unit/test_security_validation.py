"""Unit tests for input validation and security hardening.

Tests input sanitisation, email/UEN validation, query length limits,
and security configuration constants.
"""

from __future__ import annotations

from hr_advisory.security.validation import (
    CORS_CONFIG,
    SECURITY_HEADERS,
    sanitise_input,
    validate_email,
    validate_query_length,
    validate_uen,
)


class TestInputSanitisation:
    """Test XSS prevention and input cleaning."""

    def test_normal_text_unchanged(self) -> None:
        """Normal text should pass through unchanged."""
        assert sanitise_input("What is my CPF rate?") == "What is my CPF rate?"

    def test_html_escaped(self) -> None:
        """HTML special characters should be escaped."""
        result = sanitise_input('<script>alert("xss")</script>')
        assert "<script>" not in result
        assert "&lt;" in result

    def test_null_bytes_stripped(self) -> None:
        """Null bytes should be removed."""
        result = sanitise_input("hello\x00world")
        assert "\x00" not in result
        assert "helloworld" in result

    def test_truncation(self) -> None:
        """Input exceeding MAX_QUERY_LENGTH should be truncated."""
        long_input = "a" * 5000
        result = sanitise_input(long_input)
        assert len(result) == 2000

    def test_quotes_escaped(self) -> None:
        """Quotes should be escaped."""
        result = sanitise_input('He said "hello"')
        assert "&quot;" in result


class TestEmailValidation:
    """Test email format validation."""

    def test_valid_email(self) -> None:
        valid, msg = validate_email("user@example.com")
        assert valid is True
        assert msg == ""

    def test_empty_email(self) -> None:
        valid, msg = validate_email("")
        assert valid is False
        assert "required" in msg.lower()

    def test_invalid_format(self) -> None:
        valid, msg = validate_email("not-an-email")
        assert valid is False

    def test_too_long(self) -> None:
        valid, msg = validate_email("a" * 250 + "@b.com")
        assert valid is False
        assert "long" in msg.lower()

    def test_sg_domain(self) -> None:
        valid, _ = validate_email("hr@company.com.sg")
        assert valid is True


class TestUenValidation:
    """Test Singapore UEN format validation."""

    def test_valid_uen(self) -> None:
        valid, msg = validate_uen("200012345A")
        assert valid is True

    def test_empty_uen(self) -> None:
        valid, msg = validate_uen("")
        assert valid is False
        assert "required" in msg.lower()

    def test_too_short(self) -> None:
        valid, msg = validate_uen("ABC")
        assert valid is False

    def test_case_insensitive(self) -> None:
        """UEN validation should be case-insensitive."""
        valid, _ = validate_uen("200012345a")
        assert valid is True


class TestQueryLengthValidation:
    """Test advisory query length validation."""

    def test_valid_length(self) -> None:
        valid, msg = validate_query_length("What is the CPF rate for citizens?")
        assert valid is True

    def test_too_short(self) -> None:
        valid, msg = validate_query_length("Hi")
        assert valid is False
        assert "at least" in msg.lower()

    def test_too_long(self) -> None:
        valid, msg = validate_query_length("a" * 3000)
        assert valid is False
        assert "exceed" in msg.lower()


class TestSecurityConfig:
    """Test security configuration constants."""

    def test_cors_no_wildcard(self) -> None:
        """CORS should not allow wildcard origins."""
        assert "*" not in CORS_CONFIG["allow_origins"]

    def test_security_headers_hsts(self) -> None:
        """HSTS header should be configured."""
        assert "Strict-Transport-Security" in SECURITY_HEADERS

    def test_security_headers_csp(self) -> None:
        """Content-Security-Policy header should be configured."""
        assert "Content-Security-Policy" in SECURITY_HEADERS

    def test_security_headers_frame_deny(self) -> None:
        """X-Frame-Options should be set to DENY."""
        assert SECURITY_HEADERS["X-Frame-Options"] == "DENY"

    def test_security_headers_nosniff(self) -> None:
        """X-Content-Type-Options should be set to nosniff."""
        assert SECURITY_HEADERS["X-Content-Type-Options"] == "nosniff"
