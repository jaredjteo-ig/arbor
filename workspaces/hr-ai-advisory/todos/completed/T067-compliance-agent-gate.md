# T067 — Wire ComplianceAgent as Mandatory Post-Specialist Quality Gate

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T063, T064

## What to build

`ComplianceAgent` exists but is never invoked in the live pipeline. For any query touching 2 or more specialist domains, run `ComplianceAgent` after all specialists return their outputs, before passing to `ResponseSynthesizerAgent`. The compliance agent checks for cross-domain contradictions (e.g., EA notice period advice conflicts with contract terms advice) and flags them. Pass the compliance check result to the synthesizer so it can resolve conflicts explicitly.

## Acceptance Criteria

- [ ] `ComplianceAgent.check()` called when 2+ specialists responded
- [ ] `ComplianceAgent` receives all specialist outputs as input
- [ ] Returns: `contradictions: list[str]`, `risk_escalation: bool`, `override_risk_tier: str | None`
- [ ] If contradictions found, synthesizer receives them and must address each one
- [ ] If `override_risk_tier` is set (e.g., compliance agent upgrades green to amber), final response uses the higher tier
- [ ] `ComplianceAgent` skipped (with log) for single-domain queries to avoid unnecessary latency
- [ ] Integration test: query touching EA + CPF receives compliance check
- [ ] Integration test: contradictory EA/CPF advice detected and flagged in final response

## Files

- `src/hr_advisory/api/routers/advisory.py` — insert ComplianceAgent call in multi-domain path
- `src/hr_advisory/agents/compliance.py` — verify interface matches expected inputs/outputs
- `src/hr_advisory/agents/response_synthesizer.py` — add `compliance_result` parameter

## Definition of Done

- [ ] ComplianceAgent wired and called on all multi-domain queries
- [ ] Contradiction detection test passes
- [ ] Risk tier escalation from ComplianceAgent honoured in final response
- [ ] Single-domain queries not slowed down by compliance check
