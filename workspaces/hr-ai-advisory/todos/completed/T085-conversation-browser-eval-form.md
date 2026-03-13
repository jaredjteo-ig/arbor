# T085 — Conversation Browser and Evaluation Form (Frontend)

**Status**: ACTIVE
**Milestone**: 9 — Human QA Workflow
**Priority**: HIGH
**Estimated Effort**: 6h
**Dependencies**: T083, T084

## What to build

The core QA reviewer interface: a two-panel view where the left panel shows the conversation list for the active session, and the right panel shows the selected conversation in full detail with an evaluation form. Reviewers read the conversation (including specialist outputs and trust chain), score 8 dimensions, flag citations, write corrections, and submit the evaluation.

## Acceptance Criteria

### Conversation List (left panel)

- [ ] Shows all conversations in session, sorted by session filter priority (e.g., lowest-confidence first)
- [ ] Each item: date/time, query preview (first 60 chars), risk tier badge, confidence score, evaluated/pending status
- [ ] Clicking a conversation loads it in the right panel
- [ ] Evaluated conversations marked with a checkmark; remaining count shown in header

### Conversation Detail (right panel)

- [ ] Full conversation rendered with alternating user/assistant bubbles
- [ ] Each assistant turn has expandable "Specialist Outputs" section: per-specialist advice summary, confidence score, provisions retrieved
- [ ] Each assistant turn has expandable "Trust Chain" section: genesis record, attestations, chain confidence, any constraint violations
- [ ] Expandable sections collapsed by default to keep the view clean

### Evaluation Form

- [ ] 8 rubric dimension scores (1-5 radio buttons), each with a label and a brief criteria hint on hover
- [ ] Dimension labels: Legal Accuracy, Contextual Relevance, Conversational Coherence, Actionability, Risk Awareness, Citation Quality, Language Understanding, Completeness
- [ ] Citation flags section: list of citations found in the response, each with status radio (correct / incorrect / missing provision)
- [ ] "Material correction needed" toggle — when on, shows free-text correction input
- [ ] Failure category dropdown (legal_error, missing_citation, wrong_risk_tier, incomplete_answer, hallucination, coherence_failure, other) — required when material correction toggled on
- [ ] Affected agent dropdown — required when failure category selected
- [ ] Submit button posts to `POST /admin/qa/evaluations`
- [ ] After submit: left panel marks conversation as evaluated, auto-advances to next pending conversation

### Session Summary View

- [ ] Available when all conversations in session are evaluated
- [ ] Shows aggregate scores per dimension (bar chart)
- [ ] Failure category breakdown (pie chart or grouped count)
- [ ] "Complete Session" button — changes session status to completed

## Files

- `apps/web/src/components/admin/ConversationBrowser.tsx` — two-panel layout
- `apps/web/src/components/admin/ConversationDetail.tsx` — right panel with expandable sections
- `apps/web/src/components/admin/EvaluationForm.tsx` — form component
- `apps/web/src/components/admin/SessionSummaryView.tsx` — post-evaluation summary

## Reference

12-human-qa-workflow-design.md Sections 2.2, 2.3, 2.4

## Definition of Done

- [ ] Reviewer can complete a full evaluation session without page reload
- [ ] Expandable specialist outputs and trust chain sections work correctly
- [ ] Form validation: cannot submit without all 8 dimension scores
- [ ] Auto-advance to next conversation after submit
- [ ] Session summary view shows correct aggregate calculations
