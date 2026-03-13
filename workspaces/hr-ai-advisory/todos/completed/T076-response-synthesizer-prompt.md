# T076 — Enhance ResponseSynthesizer with Structured Output and Conflict Resolution

**Status**: ACTIVE
**Milestone**: 7 — Specialist Prompt Optimization
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T067, T070

## What to build

`ResponseSynthesizerAgent` currently merges specialist outputs without structure guidance. Add a mandatory response template, tone rules, length guidance keyed to risk tier, and explicit conflict resolution instructions (especially for the compliance agent output from T067). The synthesizer must produce responses that a non-lawyer Singapore SME owner can act on.

## Acceptance Criteria

- [ ] Response template enforced in system prompt:
  1. **Summary** (1-2 sentences: the direct answer)
  2. **What the law says** (provisions that apply, cited)
  3. **What you need to do** (numbered action steps)
  4. **Watch out for** (risks, deadlines, escalation triggers — omit if none)
  5. **Disclaimer** (risk-tier appropriate, from T046 system)
- [ ] Tone rules: plain English; no legalese; Singapore English acceptable; no condescension; treat the reader as capable
- [ ] Length guidance: green tier = 200-350 words; amber tier = 350-500 words; red tier = 500-700 words + explicit "consult a lawyer" call-to-action
- [ ] Conflict resolution: if `compliance_result` contains contradictions, synthesizer must name the contradiction and state which provision takes precedence or that the user must seek advice on the conflict
- [ ] Partial confidence: if any specialist confidence < 0.4, include a "Based on limited information" prefix and do not use definitive language ("you must" → "you may need to")
- [ ] Citations formatted as: `[Employment Act s.38]` inline, with full citation in a "Sources" section at end
- [ ] Integration test: multi-domain response has all 5 template sections
- [ ] Integration test: red tier response ends with explicit lawyer consultation call-to-action

## Files

- `src/hr_advisory/agents/response_synthesizer.py` — rewrite `_generate_system_prompt()`, add conflict resolution and partial confidence logic

## Reference

11-agent-architecture-analysis.md Section 3.4 ResponseSynthesizerAgent

## Definition of Done

- [ ] All 5 template sections present in 10 consecutive test responses
- [ ] Length guidance respected (responses not truncated or padded beyond ranges)
- [ ] Conflict resolution message clear and actionable (not "there is a conflict" — states what the conflict is)
