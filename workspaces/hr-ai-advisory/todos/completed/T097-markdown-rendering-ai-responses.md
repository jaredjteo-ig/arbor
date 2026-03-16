# T097 — Add Markdown Rendering for AI Responses

**Status**: ACTIVE
**Milestone**: 11 — AI Trust and Safety
**Priority**: HIGH
**Estimated Effort**: 3h
**Dependencies**: T026, T076

## What to build

AI advisory responses are currently rendered as plain text with `white-space: pre-wrap`. This means structured output from the ResponseSynthesizer (headings, bullet lists, bold terms, links) appears as raw markdown symbols rather than formatted content. Install `react-markdown` with `rehype-sanitize` and replace the plain text renderer in SystemMessage with a proper markdown renderer. This makes structured answers significantly easier to read and scan, which is critical when responses list obligations, calculate amounts, or enumerate exceptions.

## Acceptance Criteria

### Library Installation

- [ ] `react-markdown` installed and added to `apps/web/package.json`
- [ ] `rehype-sanitize` installed as the sanitization plugin (blocks XSS vectors)
- [ ] No other markdown libraries added (avoid redundancy)

### Rendering

- [ ] System message content rendered via `<ReactMarkdown>` with rehype-sanitize plugin
- [ ] Headings (# ## ###) render as visually distinct heading elements, sized consistently with design tokens
- [ ] Unordered lists (-) render as bullet points
- [ ] Ordered lists (1.) render as numbered lists
- [ ] Bold (**text**) renders as bold
- [ ] Inline code (`code`) renders as code
- [ ] Links render as styled anchor tags that open in a new tab with rel="noopener noreferrer"
- [ ] Line breaks handled correctly (blank lines produce paragraph breaks)

### Safety

- [ ] rehype-sanitize configured to strip dangerous attributes (onclick, onerror, style with expressions)
- [ ] External links in AI responses open in new tab (target="\_blank") with rel="noopener noreferrer"
- [ ] Images in AI output are blocked (AI should not produce image tags, but strip defensively)

### Style Consistency

- [ ] Rendered markdown elements use design token font sizes, colours, and spacing
- [ ] List items have consistent left-padding matching the surrounding UI
- [ ] Heading levels inside chat bubbles are visually subordinate (not h1 heading-sized)

## Files

- `apps/web/package.json` — add react-markdown, rehype-sanitize
- `apps/web/src/components/advisory/SystemMessage.tsx` — replace plain text render with ReactMarkdown
- `apps/web/src/styles/markdown.css` (or equivalent) — scoped styles for rendered markdown elements

## Definition of Done

- [ ] All AI responses render markdown formatting correctly
- [ ] rehype-sanitize is applied on every render
- [ ] Plain text responses (no markdown) render identically to before
- [ ] No XSS vectors introduced (verified by code review)
- [ ] All existing SystemMessage tests pass with the new renderer
