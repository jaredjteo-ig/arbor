# T098 — Add Stop-Generation Button and Reasoning Trace

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: MEDIUM
**Estimated Effort**: 4h
**Dependencies**: T026, T065

## What to build

Show a "Stop generating" button during active SSE streaming so the user can cancel a response. Wire this to the existing `abortRef` (or create one) that terminates the SSE connection. Replace the current generic skeleton loader with phased status indicators that communicate what the AI is actually doing at each stage. The SSE start event (or a synthetic one) should trigger the first phase indicator, and subsequent events should advance through the phases. This turns the "loading spinner" into a transparent, trust-building trace of the AI's reasoning process.

## Acceptance Criteria

### Stop Generation Button

- [ ] A "Stop generating" button appears in the ChatInput area during SSE streaming
- [ ] Clicking it aborts the SSE connection and stops the response mid-stream
- [ ] Any partial response already streamed is displayed (not discarded)
- [ ] Button disappears immediately after clicking (streaming stopped)
- [ ] After stopping, the user can send a new message normally

### Phased Status Indicators

- [ ] Three phased status messages shown during generation (replacing generic skeleton):
  1. "Searching knowledge base..." — shown immediately when streaming begins
  2. "Analysing provisions..." — shown after the first SSE token or a 1.5s timeout
  3. "Generating response..." — shown once substantive content begins streaming
- [ ] Phases advance automatically; if response is fast, earlier phases may appear briefly
- [ ] Once actual content starts streaming, status indicators are hidden and content shown
- [ ] Indicators use the existing loading/pulse animation from the design system

### Implementation

- [ ] Use or create an `abortRef` (React ref holding an AbortController) in ChatContainer
- [ ] Pass abort function down to ChatInput for button wiring
- [ ] Phase state managed in ChatContainer streaming state machine
- [ ] SSE start event (if present in API) used to trigger phase 1; synthesise a timer fallback if not

## Files

- `apps/web/src/components/advisory/ChatContainer.tsx` — streaming state machine, abortRef, phase logic
- `apps/web/src/components/advisory/ChatInput.tsx` — stop button UI, receives abort prop
- `apps/web/src/components/advisory/StreamingIndicator.tsx` — new component for phased status messages

## Definition of Done

- [ ] Stop button visible and functional during all SSE streaming responses
- [ ] Partial responses preserved after stop
- [ ] Three phased status messages shown during generation in correct order
- [ ] No regression in normal (non-stopped) streaming behaviour
- [ ] Stop button not shown when not streaming
