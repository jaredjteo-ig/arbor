# T104 — Upgrade Chat Input to Expandable Textarea

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: MEDIUM
**Estimated Effort**: 3h
**Dependencies**: T026, T093

## What to build

Replace the single-line `<input>` element in the advisory chat with an auto-expanding `<textarea>` that grows with the user's text (up to a maximum height before scrolling). Implement Shift+Enter for inserting newlines and Enter alone to send. Make the initial suggestion chips context-aware: if a company profile exists, show suggestions relevant to the company's industry or employee count; if not, show generic starter questions. This makes the advisory interface more capable and immediately welcoming.

## Acceptance Criteria

### Auto-Expanding Textarea

- [ ] Single-line `<input>` replaced with `<textarea>` in both design-system/ChatInput and advisory/ChatInput (or wherever the advisory chat input is rendered)
- [ ] Textarea starts at single-line height and expands as the user types
- [ ] Maximum height: 5 lines (~120px); beyond that, the textarea scrolls internally
- [ ] Textarea shrinks back when text is deleted
- [ ] Visual appearance matches the existing input (same border, background, padding, font)

### Keyboard Behaviour

- [ ] Enter key sends the message (unless shift is held)
- [ ] Shift+Enter inserts a newline without sending
- [ ] Ctrl+Enter (or Cmd+Enter) also sends (secondary shortcut)
- [ ] Textarea clears and returns to single-line height after sending
- [ ] Focus returns to textarea after sending

### Context-Aware Suggestion Chips

- [ ] If company profile is present: suggestion chips use company industry/context (e.g., "What CPF rates apply to my part-time staff?" for F&B industry)
- [ ] If no company profile: suggestion chips show generic starter questions (e.g., "What are the notice period rules in Singapore?", "How do I calculate CPF for a new hire?")
- [ ] Chips are limited to 3 at a time to avoid clutter
- [ ] Chips disappear once the user starts typing or sends a message
- [ ] Chips reappear when a new conversation is started

## Files

- `apps/web/src/components/design-system/ChatInput.tsx` — replace input with auto-expanding textarea
- `apps/web/src/components/advisory/ChatContainer.tsx` — update to pass company context to suggestion chips
- `apps/web/src/components/advisory/SuggestionChips.tsx` — new or updated component for context-aware chips

## Definition of Done

- [ ] Textarea expands correctly as text is typed
- [ ] Enter sends, Shift+Enter creates newlines
- [ ] Textarea clears and collapses after sending
- [ ] Suggestion chips are context-aware (different for users with/without company profile)
- [ ] No regression in mobile layout
