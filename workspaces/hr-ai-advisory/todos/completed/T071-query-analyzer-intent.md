# T071 — Enhance QueryAnalyzer with Intent Detection and Few-Shot Examples

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T063

## What to build

`QueryAnalyzerAgent` currently classifies domains but does not detect the user's intent (are they asking for advice, requesting a calculation, needing a document, or in an emergency?). Add an `intent` field to `QueryAnalysisResult` with values: ADVISORY, CALCULATION, DOCUMENT, EMERGENCY, COMPLIANCE_CHECK, CLARIFICATION_NEEDED. Add routing logic so action intents bypass specialists and go directly to the relevant action agent (CalculatorAgent, DocumentGenerationAgent, EmergencyResponse). Add few-shot classification examples to the system prompt to reduce misclassification.

## Acceptance Criteria

- [ ] `QueryAnalysisResult` includes `intent: str` field
- [ ] Six intent values handled: ADVISORY, CALCULATION, DOCUMENT, EMERGENCY, COMPLIANCE_CHECK, CLARIFICATION_NEEDED
- [ ] System prompt includes at least 6 few-shot classification examples (one per intent type)
- [ ] CALCULATION intent routes to CalculatorAgent directly, skipping specialists
- [ ] DOCUMENT intent routes to DocumentGenerationAgent directly
- [ ] EMERGENCY intent routes to EmergencyResponse module directly
- [ ] CLARIFICATION_NEEDED intent triggers QueryClarifier (T077) or returns clarifying question to user
- [ ] ADVISORY intent uses normal specialist dispatch (T063)
- [ ] Integration test: "calculate my CPF contribution for $3,200 salary" classified as CALCULATION, not ADVISORY
- [ ] Integration test: "I need a resignation letter template" classified as DOCUMENT

## Files

- `src/hr_advisory/agents/query_analyzer.py` — add intent field, few-shot examples, intent detection logic
- `src/hr_advisory/api/routers/advisory.py` — add intent-based routing branch

## Reference

11-agent-architecture-analysis.md Section 3.1 QueryAnalyzerAgent, Section 2.1 Change 3

## Definition of Done

- [ ] Intent detection accuracy > 90% on 20 hand-labelled test queries
- [ ] All 6 intents route correctly to their destination
- [ ] No ADVISORY query incorrectly sent to CALCULATION or DOCUMENT path
