# P5-AD — Advisory orphan history rows

**Source:** `04-validate/13-redteam-comprehensive-2026-05-19.md`
finding O3 / C9.

**State:** Live walk surfaced 2 conversations in the History sidebar
with `"(earlier reply unavailable)"` placeholder text below the
question. They're real persisted conversations whose assistant turn
was the legacy guardrail-fallback string ("I'm having trouble
processing your question right now…"). The frontend rewrites that
into a placeholder on render via `cleanPreview`. Buyer sees them as
"things this platform lost". Backend side already fixed in
round-3 (advisory engine pre-classifier + force search_kb), but the
historical rows persist.

---

## P5-AD-1 — Purge legacy advisory rows on prod

- **Symptom:** sidebar History entries with `"(earlier reply
  unavailable)"`. Frontend logs no error; data exists in
  `AdvisoryConversation` / `AdvisoryMessage` tables with the legacy
  fallback string stored as the assistant turn.
- **Where:** prod Postgres. Frontend cosmetic substitution is in
  `apps/web/src/app/(dashboard)/advisory/page.tsx:43-48`.
- **Fix (two parts):**
  1. **One-time prod DB purge.** Either:
     - SQL: `DELETE FROM advisory_messages WHERE content LIKE
       'I''m having trouble processing your question%';` followed by
       `DELETE FROM advisory_conversations WHERE id NOT IN
       (SELECT DISTINCT conversation_id FROM advisory_messages);`
     - OR a `scripts/maintenance/purge_legacy_advisory.py` script
       (preferred — auditable, can be re-run).
  2. **Backend filter going forward.** In the advisory engine, never
     persist a conversation if the assistant turn matches the legacy
     fallback regex. The pre-classifier fix from round-3 should
     prevent new ones, but defence-in-depth.
- **Acceptance:**
  - Owner + HR + Marcus all see ZERO "(earlier reply unavailable)"
    entries in `/advisory` History after deploy.
  - `SELECT COUNT(*) FROM advisory_messages WHERE content LIKE
    'I''m having trouble%'` returns 0.
  - Backend log shows no new rows of that shape created in the
    week after deploy.
- **Regression test:**
  `tests/regression/test_p5_ad_no_legacy_advisory_rows.py`:
  source-pin that the advisory engine post-write check refuses
  to persist a turn matching the legacy fallback regex.

---

## P5-AD-2 — Conversations-list cache invalidation (smaller fix)

- **Symptom:** observed in live walk — on first paint /advisory
  showed 3 conversations in sidebar but `/api/advisory/conversations`
  returned only 1 on subsequent refresh. React Query held stale
  pre-delete rows.
- **Where:** `apps/web/src/app/(dashboard)/advisory/page.tsx`,
  `handleConversationStart` calls `refreshConversations()` on success
  but error paths don't invalidate.
- **Fix:** add `queryClient.invalidateQueries({ queryKey:
  ['advisoryConversations'] })` on SSE error AND on delete.
- **Acceptance:** delete a conversation → sidebar updates immediately
  without manual refresh. SSE error → sidebar reflects the failed
  turn (or omits it).
- **Regression test:** Playwright E2E in next red-team round.

---

## Effort + dependencies

- Total: 1.5 hours
- DB op requires `ADMIN_PASSWORD` env var on prod (per
  `.claude/rules/seeding.md` rule 2 + 3).
- DEPLOY ordering: ship the purge script first, run it on prod, then
  ship the backend filter + frontend cache fix.
