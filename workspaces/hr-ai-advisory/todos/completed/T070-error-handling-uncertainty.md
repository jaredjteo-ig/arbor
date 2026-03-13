# T070 — Fix Error Handling to Escalate Uncertainty Instead of Suppressing It

**Status**: ACTIVE
**Milestone**: 6 — Advisory Pipeline Architecture
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T063

## What to build

All agents currently default to `risk_tier="green"` and `confidence=0.5` on exceptions — the wrong failure mode for a regulatory advisory system. When an agent cannot determine the answer, silently returning a medium-confidence green response may mislead users into believing everything is fine. Change defaults so that errors produce amber risk tier, explicit low confidence (0.3), and a user-visible "could not determine" message. Add uncertainty signaling to the synthesizer when one or more specialists returned with low confidence.

## Acceptance Criteria

- [ ] All specialist `advise()` error handlers default to: `risk_tier="amber"`, `confidence=0.3`, `advice="I could not determine a reliable answer for this question. Please consult an employment lawyer or MOM directly."`
- [ ] `ResponseSynthesizerAgent` detects when any specialist confidence < 0.4 and includes a "partial confidence" warning in the response
- [ ] Pipeline-level exception handler (in advisory.py) returns amber response with explicit uncertainty, not a 500 error that surfaces to the user as a technical failure
- [ ] If 2+ specialists return low confidence, final risk tier is upgraded to red and professional consultation is recommended
- [ ] Integration test: simulated specialist LLM failure returns amber response with uncertainty message
- [ ] Integration test: two low-confidence specialists trigger red tier escalation

## Files

- `src/hr_advisory/agents/specialists/_base.py` — update error handler defaults
- `src/hr_advisory/agents/specialists/employment_act.py` — update error defaults
- `src/hr_advisory/agents/specialists/cpf.py` — update error defaults
- `src/hr_advisory/agents/specialists/foreign_manpower.py` — update error defaults
- `src/hr_advisory/agents/specialists/fair_employment.py` — update error defaults
- `src/hr_advisory/agents/specialists/tax.py` — update error defaults
- `src/hr_advisory/agents/specialists/wsh.py` — update error defaults
- `src/hr_advisory/agents/response_synthesizer.py` — add partial confidence handling
- `src/hr_advisory/api/routers/advisory.py` — update pipeline error handler

## Definition of Done

- [ ] No specialist returns green/0.5 on error
- [ ] Partial confidence warning visible in frontend chat response
- [ ] Error handling unit tests cover all specialist classes
