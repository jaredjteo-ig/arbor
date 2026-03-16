# T101 — Wire Conversation History Loading

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T026, T065, T101

## What to build

Connect the `useAdvisoryHistory` hook to the conversation sidebar so that clicking a past conversation loads and displays its messages in the main chat area. Auto-title conversations from the text of the first user message (truncated to ~60 chars) instead of leaving them untitled. Add a context menu on each conversation item in the sidebar with Delete and Rename options. This makes the advisory page a persistent, navigable knowledge store rather than a single ephemeral chat.

## Acceptance Criteria

### Conversation Loading

- [ ] Clicking a conversation in ConversationSidebar loads its messages into the chat area
- [ ] Messages display in correct chronological order (oldest first)
- [ ] Loaded conversation is visually highlighted as active in the sidebar
- [ ] Loading state shown while messages are fetched (skeleton or spinner)
- [ ] Error state shown if conversation cannot be loaded (with retry option)

### Auto-Titling

- [ ] New conversations are automatically titled from the first user message (first 60 characters, trimmed)
- [ ] If the message is shorter than 60 chars, the full message is used as the title
- [ ] Title updates in the sidebar immediately after the first message is sent (optimistic update acceptable)
- [ ] Untitled conversations from before this change show a fallback title: "Conversation [date]"

### Context Menu

- [ ] Right-click (or three-dot icon) on a conversation item shows a context menu with: Rename, Delete
- [ ] Rename: opens an inline text input in the sidebar, saves on Enter or blur
- [ ] Delete: shows a confirmation dialog before deleting; removes conversation from sidebar on confirm
- [ ] After deletion of the active conversation, the chat area clears or switches to a new conversation

## Files

- `apps/web/src/app/(dashboard)/advisory/page.tsx` — wire conversation selection to message loading
- `apps/web/src/components/advisory/ConversationSidebar.tsx` — add context menu, active state, title display
- `apps/web/src/hooks/useAdvisoryHistory.ts` — connect to real API, expose selected conversation loader
- `src/hr_advisory/api/routers/advisory.py` — ensure conversation message history endpoint exists

## Definition of Done

- [ ] Clicking a past conversation loads its messages correctly
- [ ] New conversations show an auto-generated title from first message
- [ ] Rename and Delete work via context menu
- [ ] Deletion of active conversation handled gracefully
- [ ] All conversation sidebar interactions feel responsive (no noticeable lag)
