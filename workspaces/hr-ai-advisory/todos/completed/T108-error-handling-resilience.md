# T108 — Error Handling and Resilience

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: HIGH
**Estimated Effort**: 5h
**Dependencies**: T026, T098

## What to build

Fix four identified resilience gaps: (1) technical error messages leaking to users (map all API errors to user-friendly text), (2) SSE connection drops not retried (add reconnection with exponential backoff), (3) advisory page height calculation using an incorrect offset (fix the 64px vs 56px top bar height mismatch and use dvh units), and (4) mutation success states not surfaced (add toast notifications). These are the kind of rough edges that make an otherwise complete product feel unfinished.

## Acceptance Criteria

### Error Message Sanitization

- [ ] Create a central error mapping function that converts API/SSE errors to user-friendly messages:
  - Network errors: "Connection lost. Check your internet and try again."
  - 401/403: "Your session has expired. Please log in again." (with redirect)
  - 429 (rate limit): "You have sent too many requests. Please wait a moment."
  - 500/503: "Arbor is temporarily unavailable. Please try again in a few minutes."
  - Timeout: "The response took too long. Try a shorter question."
- [ ] No raw error messages, status codes, or stack traces visible to users anywhere in the application
- [ ] Error mapping applied consistently in advisory chat, calculator pages, and form submissions

### SSE Reconnection

- [ ] SSE connection drops during advisory streaming trigger automatic reconnection
- [ ] Reconnection uses exponential backoff: 1s, 2s, 4s, max 30s
- [ ] After 3 failed reconnection attempts, show user-facing error: "Connection lost — try sending your question again."
- [ ] Reconnection state shown subtly to the user (e.g., "Reconnecting..." in the streaming indicator)
- [ ] Successful reconnection resumes the in-progress response if the backend supports it; otherwise starts fresh

### Advisory Page Height Fix

- [ ] Replace hardcoded `calc(100vh - 64px)` with `calc(100dvh - 56px)` (or the correct top bar height from design tokens)
- [ ] Verify the top bar height value in TopBar.tsx and use the same value in the advisory page height calc
- [ ] Test on mobile browsers (where dvh vs vh differs due to address bar)
- [ ] No content cut off or overflowing at the bottom of the advisory chat on any screen size

### Toast Notifications for Mutations

- [ ] Add toast notifications for all key mutation success states:
  - Escalation submitted: "Request sent — a specialist will contact you shortly."
  - Company profile saved: "Profile updated successfully."
  - Document generated: "Document ready — check your downloads."
  - Conversation deleted: "Conversation deleted."
  - Conversation renamed: "Conversation renamed."
- [ ] Toast appears in the bottom-right corner, auto-dismisses after 4 seconds
- [ ] Toast can be manually dismissed via a close button
- [ ] Use existing toast/notification component if present; create a simple one if not

## Files

- `apps/web/src/services/api/sse.ts` — add reconnection with exponential backoff
- `apps/web/src/services/api/errors.ts` — new file: error mapping function
- `apps/web/src/components/advisory/ChatContainer.tsx` — apply error mapping, height fix, reconnect state
- `apps/web/src/app/(dashboard)/advisory/page.tsx` — fix height calc to dvh with correct offset
- `apps/web/src/components/shared/Toast.tsx` — new or existing toast component
- `apps/web/src/components/shared/ToastProvider.tsx` — context provider for toasts

## Definition of Done

- [ ] No raw API errors or status codes visible in the UI
- [ ] SSE reconnects automatically with exponential backoff on connection drop
- [ ] Advisory page chat area fills the viewport correctly on all screen sizes and browsers
- [ ] Toast notifications appear for all listed mutation success states
- [ ] Toast dismisses automatically and manually
