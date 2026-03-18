# T107 — Contextual AI Entry Points

**Status**: ACTIVE
**Milestone**: 12 — Enterprise Polish
**Priority**: MEDIUM
**Estimated Effort**: 4h
**Dependencies**: T035, T031, T036, T026

## What to build

Add "Ask Arbor about this" prompts at contextually relevant moments throughout the product. On the compliance page, add a prompt on each amber or red domain card (the user is already looking at a problem — help them resolve it). On calculator result pages, add an interpretation prompt (the user has a number — they need to know what to do with it). On the document generation page, add a prompt for guidance on which template to use. In the advisory chat, link emergency playbooks from red-tier responses. These entry points collapse the distance between "seeing a problem" and "getting help."

## Acceptance Criteria

### Compliance Page — Per-Domain Prompt

- [ ] Each amber or red compliance domain card shows an "Ask Arbor about this" button
- [ ] Clicking it opens the advisory side panel (or navigates to /advisory) pre-filled with a contextual query: "My [domain] compliance score is [amber/red]. What do I need to fix?"
- [ ] Green domain cards do not show the button (no problem to solve)

### Calculator Results — Interpretation Prompt

- [ ] After a calculator completes (CPF, leave, quota/levy), a contextual prompt appears:
  - CPF: "Understand what this means for your payroll" → opens advisory pre-filled with context
  - Leave: "What are my obligations for this leave entitlement?" → opens advisory
  - Quota/Levy: "How can I optimise my foreign worker quota?" → opens advisory
- [ ] The prompt includes the relevant calculation result values in the pre-filled advisory query

### Document Generation — Guidance Prompt

- [ ] On the document template selection step, a "Not sure which template to use?" link appears
- [ ] Clicking it opens the advisory pre-filled with: "Which employment document template should I use for [document purpose]?"

### Emergency Playbooks — Advisory Links

- [ ] Red-tier advisory responses that mention a specific emergency scenario include a link to the corresponding playbook in the emergency section
- [ ] Playbook link text: "See emergency playbook for [scenario]"
- [ ] Link navigates to /emergency with the relevant playbook highlighted

## Files

- `apps/web/src/app/(dashboard)/compliance/page.tsx` — add per-domain advisory prompts
- `apps/web/src/app/(dashboard)/calculators/cpf/page.tsx` — add interpretation prompt on results
- `apps/web/src/app/(dashboard)/calculators/leave/page.tsx` — add interpretation prompt on results
- `apps/web/src/app/(dashboard)/calculators/quota-levy/page.tsx` — add interpretation prompt on results
- `apps/web/src/app/(dashboard)/documents/page.tsx` — add guidance prompt
- `apps/web/src/components/advisory/SystemMessage.tsx` — add playbook link for red-tier responses
- `apps/web/src/components/shared/AskArborButton.tsx` — new shared component for the contextual prompt

## Definition of Done

- [ ] Amber/red compliance domain cards show "Ask Arbor about this" button
- [ ] All three calculator result pages show contextual interpretation prompts
- [ ] Document template page shows guidance link
- [ ] Red-tier advisory responses include emergency playbook links
- [ ] All prompts pre-fill the advisory chat with relevant context
