"""Unit tests for the abuse prevention and guardrails module.

Tests query screening (circumvention detection, escalation triggers),
response content filtering, confidence escalation, and rate limiting.
"""

from __future__ import annotations

from hr_advisory.workflows.guardrails import (
    EscalationReason,
    ScreeningResult,
    check_confidence_escalation,
    check_rate_limit,
    screen_query,
    screen_response,
)


class TestQueryScreening:
    """Test query screening for circumvention and escalation patterns."""

    def test_normal_query_passes(self) -> None:
        """A normal HR question should pass screening."""
        result = screen_query("How many days of annual leave are employees entitled to?")
        assert result.result == ScreeningResult.PASS
        assert result.matched_patterns == []

    def test_cpf_avoidance_blocked(self) -> None:
        """Attempting to avoid CPF should be blocked."""
        result = screen_query("How can I avoid paying CPF for my employees?")
        assert result.result == ScreeningResult.BLOCK
        assert "CPF" in result.reason

    def test_underpay_pwm_blocked(self) -> None:
        """Attempting to pay below PWM should be blocked."""
        result = screen_query("Can I pay less than progressive wage?")
        assert result.result == ScreeningResult.BLOCK

    def test_illegal_deductions_blocked(self) -> None:
        """Asking about illegal salary deductions should be blocked."""
        result = screen_query("How do I make illegal deductions from salary?")
        assert result.result == ScreeningResult.BLOCK

    def test_skip_overtime_blocked(self) -> None:
        """Attempting to not pay overtime should be blocked."""
        result = screen_query("How can I not pay overtime to staff?")
        assert result.result == ScreeningResult.BLOCK

    def test_fake_records_blocked(self) -> None:
        """Attempting to falsify records should be blocked."""
        result = screen_query("How to fake employment contract?")
        assert result.result == ScreeningResult.BLOCK

    def test_hire_without_permit_blocked(self) -> None:
        """Hiring without work permit should be blocked."""
        result = screen_query("Can I hire without permit?")
        assert result.result == ScreeningResult.BLOCK

    def test_avoid_ket_blocked(self) -> None:
        """Avoiding issuing KETs should be blocked."""
        result = screen_query("How to avoid providing KETs?")
        assert result.result == ScreeningResult.BLOCK

    def test_pregnancy_dismissal_blocked(self) -> None:
        """Dismissing pregnant employees should be blocked."""
        result = screen_query("Can I terminate an employee who is pregnant?")
        assert result.result == ScreeningResult.BLOCK

    def test_forced_resignation_blocked(self) -> None:
        """Forcing resignation should be blocked."""
        result = screen_query("How to force employee to resign?")
        assert result.result == ScreeningResult.BLOCK

    def test_misclassification_blocked(self) -> None:
        """Misclassifying employees to avoid obligations should be blocked."""
        result = screen_query("Can I classify as freelancer to avoid employment obligations?")
        assert result.result == ScreeningResult.BLOCK

    def test_blocked_query_provides_alternative(self) -> None:
        """Blocked queries should provide alternative guidance."""
        result = screen_query("How can I avoid paying CPF?")
        assert result.alternative_guidance != ""

    def test_litigation_escalated(self) -> None:
        """Queries involving litigation should be escalated."""
        result = screen_query("My employee is suing me, what should I do?")
        assert result.result == ScreeningResult.ESCALATE
        assert result.escalation_reason == EscalationReason.ACTIVE_LITIGATION

    def test_criminal_escalated(self) -> None:
        """Queries involving criminal matters should be escalated."""
        result = screen_query("Employee committed fraud, need to file police report")
        assert result.result == ScreeningResult.ESCALATE
        assert result.escalation_reason == EscalationReason.CRIMINAL_LIABILITY

    def test_discrimination_escalated(self) -> None:
        """Queries involving discrimination should be escalated."""
        result = screen_query("Employee filed harassment complaint")
        assert result.result == ScreeningResult.ESCALATE
        assert result.escalation_reason == EscalationReason.DISCRIMINATION_ALLEGATION

    def test_cross_border_escalated(self) -> None:
        """Queries involving cross-border employment should be escalated."""
        result = screen_query("How do I handle cross-border employment?")
        assert result.result == ScreeningResult.ESCALATE
        assert result.escalation_reason == EscalationReason.MULTI_JURISDICTION

    def test_escalation_takes_priority_over_block(self) -> None:
        """Escalation patterns should be checked before circumvention patterns."""
        # This query matches both escalation (lawsuit) and could theoretically
        # match circumvention patterns. Escalation should win.
        result = screen_query("Can I avoid paying if there's a lawsuit?")
        assert result.result == ScreeningResult.ESCALATE


class TestResponseScreening:
    """Test response content filtering for TAFEP compliance."""

    def test_clean_response_passes(self) -> None:
        """A clean response should pass content filtering."""
        result = screen_response(
            "Under the Employment Act, all employees are entitled to annual leave "
            "based on their years of service."
        )
        assert result.result == ScreeningResult.PASS

    def test_discriminatory_hiring_blocked(self) -> None:
        """Response suggesting discriminatory hiring should be blocked."""
        result = screen_response("You should only accept Chinese candidates for this role.")
        assert result.result == ScreeningResult.BLOCK

    def test_age_discrimination_blocked(self) -> None:
        """Response with age-discriminatory advice should be blocked."""
        result = screen_response("Set an age limit of 40 for new hires.")
        assert result.result == ScreeningResult.BLOCK

    def test_pregnancy_discrimination_blocked(self) -> None:
        """Response suggesting pregnancy discrimination should be blocked."""
        result = screen_response("Don't hire pregnant candidates.")
        assert result.result == ScreeningResult.BLOCK


class TestConfidenceEscalation:
    """Test confidence-based escalation."""

    def test_high_confidence_no_escalation(self) -> None:
        """High confidence should not trigger escalation."""
        result = check_confidence_escalation(0.9)
        assert result is None

    def test_medium_confidence_no_escalation(self) -> None:
        """Medium confidence (>= 0.5) should not trigger escalation."""
        result = check_confidence_escalation(0.5)
        assert result is None

    def test_low_confidence_escalation(self) -> None:
        """Low confidence (< 0.5) should trigger escalation."""
        result = check_confidence_escalation(0.3)
        assert result is not None
        assert result.result == ScreeningResult.ESCALATE
        assert result.escalation_reason == EscalationReason.LOW_CONFIDENCE


class TestRateLimiting:
    """Test in-memory rate limiting."""

    def test_first_request_allowed(self) -> None:
        """First request should always be allowed."""
        assert check_rate_limit("test-user-unique-1") is True

    def test_rate_limit_enforced(self) -> None:
        """Exceeding rate limit should return False."""
        from hr_advisory.workflows.guardrails import _MAX_REQUESTS_PER_WINDOW

        user_id = "test-rate-limit-user"
        for _ in range(_MAX_REQUESTS_PER_WINDOW):
            check_rate_limit(user_id)
        # The next request should be blocked.
        assert check_rate_limit(user_id) is False
