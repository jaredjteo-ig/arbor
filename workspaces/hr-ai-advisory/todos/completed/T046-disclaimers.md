# T046 — Disclaimers

**Status**: Completed
**Date**: 2026-03-12

## What was built

**Risk-Tiered Disclaimer Framework**:

- `VerificationDepth` enum (GREEN, AMBER, RED) mapping to verification intensity
- `DisclaimerContent` frozen dataclass with risk tier, disclaimer/framing text, professional referral flag, verification depth, and human review queue status

**Platform Disclaimer**:

- `PLATFORM_DISCLAIMER` constant — persistent footer stating AITE provides HR information (not legal advice), recommending professional verification for critical decisions, and noting professional indemnity insurance

**Per-Response Disclaimer Logic**:

- `get_disclaimer()` — returns tier-appropriate disclaimer content based on risk tier and confidence score
- GREEN: no per-query disclaimer; source citation provides transparency
- AMBER: light domain-specific framing (e.g., "Based on current Employment Act provisions...") with 7 domain framings
- RED: strong disclosure with professional referral recommendation; also triggers for any confidence score below 0.5; queues for human review

**Verification Gradient**:

- `VerificationResult` frozen dataclass tracking which checks were applied and their pass/fail status
- `apply_verification_gradient()` — applies graduated verification depth:
  - GREEN: citation validation only
  - AMBER: citation + confidence threshold (0.6) + cross-domain consistency
  - RED: all AMBER checks + human review queued

**Addresses**: R2-GAP3 (risk-tiered disclaimers)

## Files

- `src/hr_advisory/trust/disclaimers.py` — disclaimer and verification gradient module
