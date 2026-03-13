# T026 — Advisory Chat Interface (React Web)

## Status: COMPLETED

## What Was Built

### Full Advisory Chat Interface

1. **ChatContainer** (`components/advisory/ChatContainer.tsx`)
   - SSE streaming via `advisoryApi.stream()` — word-by-word response rendering
   - User/assistant message state management
   - Auto-scroll to latest message
   - Pre-filled question support from onboarding (`?q=` URL param)
   - Abort controller for stream cancellation on unmount
   - Loading skeleton during initial streaming
   - Error handling with user-friendly messages

2. **SystemMessage** (`components/advisory/SystemMessage.tsx`)
   - Risk-tier badge (green/amber/red) with confidence score
   - RED responses: red left border, warning icon header, "Connect to Employment Law Specialist" CTA
   - Source citations using SourceCitation component
   - Follow-up suggestion chips (context-aware based on risk tier and content)
   - FeedbackButtons on every completed response (thumbs up/down with text field)
   - Streaming indicator (animated cursor)

3. **ConversationSidebar** (`components/advisory/ConversationSidebar.tsx`)
   - Grouped by date: Today / This Week / This Month / Earlier
   - Search filtering by title and last message
   - Active conversation highlighting with primary border
   - Collapsible to icon-only mode
   - New conversation button
   - Hidden on mobile (md breakpoint)

4. **ContextBar** (`components/advisory/ContextBar.tsx`)
   - Collapsible company profile context bar
   - Shows company name, industry, employee count, UEN, contact info
   - Reads from AuthContext + useCompanyProfile hook

5. **Advisory Page** (`app/(dashboard)/advisory/page.tsx`)
   - Full-height layout: sidebar | chat area
   - Suspense boundary for `useSearchParams`
   - Conversation list state management
   - New conversation / select conversation handlers

### Initial Suggestions

Empty state shows 5 suggested starter questions covering leave, CPF, EA compliance, foreign worker quotas, and resignation handling.

### Follow-up Suggestions

Context-aware based on response content:
- RED tier: immediate obligations, documents needed, penalties
- AMBER tier: how to fix, deadlines, document generation
- CPF-related: calculate for specific employee, PR employees
- Leave-related: calculate entitlement, part-time employees
- General: tell me more, what should I do next

## Verification

TypeScript compiles clean (0 errors).

## Files

- `apps/web/src/components/advisory/ChatContainer.tsx`
- `apps/web/src/components/advisory/SystemMessage.tsx`
- `apps/web/src/components/advisory/ConversationSidebar.tsx`
- `apps/web/src/components/advisory/ContextBar.tsx`
- `apps/web/src/components/advisory/index.ts`
- `apps/web/src/app/(dashboard)/advisory/page.tsx` (replaced placeholder)
