# T027 — Advisory Chat Interface (Flutter Mobile)

## Status: COMPLETED

## What Was Built

### Full Advisory Chat Interface (Flutter)

Replaced placeholder `AdvisoryScreen` with a complete chat interface matching the React web version:

1. **Message list** — `ListView` with `ChatBubble` for user/system messages
2. **SSE streaming** — Token-by-token response via `AdvisoryRepository.streamQuery()` / `SSEClient`
3. **System messages** with:
   - Risk-tier left border via `ChatBubbleRiskTier`
   - `RiskTierBadge` with confidence score
   - `SourceCitation` chips for cited provisions (authority level mapped from act name)
   - RED responses: warning header, "Connect to Employment Law Specialist" CTA
   - Context-aware follow-up suggestions as `ActionChip` chips
   - `FeedbackButtons` (thumbs up/down + text) on the latest response
4. **Loading state** — Skeleton during initial streaming, animated cursor during content streaming
5. **Empty state** — Icon, heading, description, initial suggestion chips
6. **Chat input** — `ChatInput` with voice button, send button, suggestion chips, haptic feedback on send
7. **History button** — AppBar action (wired to drawer in future)
8. **Pre-fill support** — Optional `prefillQuestion` parameter from onboarding

### Follow-up Suggestions

Same logic as React:
- RED: immediate obligations, documents, penalties
- AMBER: how to fix, deadline, generate document
- CPF/leave-specific suggestions
- General: tell me more, what should I do next

### Autocorrect

`ChatInput` uses `autocorrect: true` by default per the design system. The onboarding flow already disables it for Singlish input.

## Verification

`flutter analyze` — 0 issues found.

## Files

- `apps/mobile/lib/features/advisory/screens/advisory_screen.dart` (replaced placeholder)
