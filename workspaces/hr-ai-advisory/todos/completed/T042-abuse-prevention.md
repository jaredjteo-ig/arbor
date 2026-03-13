# T042 — Abuse Prevention and Guardrails

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Query Screening Pipeline**:

- 10 circumvention detection patterns: avoid CPF, underpay PWM, illegal deductions, skip OT pay, falsify records, employ without permit, avoid KET/payslip, pregnancy-related dismissal, constructive dismissal, misclassification
- Each pattern returns a BLOCK result with explanation of why the practice is illegal and what the consequences are
- Alternative guidance offered: "Instead of seeking ways to circumvent... we can help you find compliant approaches"

**Mandatory Escalation System**:

- 4 escalation trigger patterns: active litigation, criminal liability, discrimination allegations, multi-jurisdiction matters
- `EscalationReason` enum for tracking escalation types
- Low confidence threshold check (`check_confidence_escalation()` at < 0.5)

**Content Filtering**:

- 3 response filter patterns for discriminatory hiring advice, age discrimination, pregnancy/disability discrimination
- `screen_response()` function to check AI-generated responses before delivery

**Rate Limiting**:

- Simple in-memory rate limiter (60-second window, 30 requests max)
- `check_rate_limit()` returns allow/deny per user

**Flagged Query Logging**:

- Automatic logging of all blocked and escalated queries
- `get_flagged_queries()` with optional reviewed filter
- `review_flagged_query()` for admin review workflow

## Files

- `src/hr_advisory/workflows/guardrails.py` — full guardrails module
