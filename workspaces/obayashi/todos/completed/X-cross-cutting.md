# Cross-cutting (not gated)

**Source plan:** `02-plans/03-post-redteam-plan.md` "Cross-cutting items" section.
**State:** none of these block any gate. Each can land any time.

## X-1 — Fix React missing-key warning in ClaimsList (NEW-2)

- **Source:** round-12 lap finding (full element walk).
- **Symptom:** dev console emits "Each child in a list should have a
  unique 'key' prop. Check the render method of `ClaimsList`."
- **Where:** `apps/web/src/app/(dashboard)/claims/page.tsx` — search for
  the `.map(...)` call rendering claim/items rows that's missing a `key`.
- **Constraint:** cosmetic only — does not affect prod users (warning
  doesn't surface in built output). Fix when next touching the file.
- **Acceptance:** dev console clean on `/claims` page load.

## X-2 — Triage 45 pre-existing test failures

- **Source:** baseline of `pytest tests/` shows 51 failures pre-round-12,
  45 after my recruitment_advanced fix.
- **Symptom:** old tests stub `dataflow_crud.read` but production code
  has migrated to `list_records` for tenant-scoped helper patterns
  (similar to the TestReapplyCandidate fix that landed in 92f4d32).
- **Plan:**
  1. Group failures by router (recruitment_resume, recruitment_security_fixes,
     screening_questions, hire_role_allowlist, preboarding_auto_create,
     mobile_policy_compat, etc.).
  2. For each group, decide: fix the test (matches new helper),
     fix the implementation (test reveals a real bug), or delete the test
     (covers retired surface).
  3. Land in batches of ≤ 10 tests per commit so reviewers can verify.
- **Acceptance:** `pytest tests/` baseline reaches < 5 failures (or 0
  if all groups land cleanly).

## X-3 — Codify round-12 patterns into security-patterns.md

- **Source:** round-12 closure introduced 4–5 reusable patterns.
- **Patterns to codify into `.claude/skills/project/security-patterns.md`:**
  1. **Cache-bypass-on-recalc** (B3) — any function that READs then
     WRITES a derived aggregate (claim totals, leave balances, headcount)
     must pass `cache_ttl=0` to the read; otherwise the write lags one
     event behind. Symptom: aggregates equal "last item only".
  2. **Defensive route guard** (B2) — Next.js App Router groups can
     unintentionally expose an `(auth)/X/page.tsx` at `/X` to logged-in
     users. Defence: `useEffect` redirect on already-onboarded
     conditions; assume bookmarks/back-button reach any URL.
  3. **Chronological-ordering guard** (H3) — any "mark paid" /
     "publish" / "finalize" workflow must reject the action when an
     earlier-period sibling is still draft. CPF/IR8A/payroll
     sequencing depends on this.
  4. **Unique-name helper** (H4) — `_ensure_unique_template_name`
     pattern (case-insensitive, whitespace-collapsed, scoped by
     company + active flag) is the right shape for any user-named
     resource. Plus the auto-suffix pattern for "duplicate" endpoints.
  5. **Live-vs-snapshot drift** (NEW-3) — Company snapshot fields
     (headcount\_\*, etc.) drift from live employee state. Any tile/card/
     report that's user-facing should compute live, not read snapshots.
- **Format:** follow the numbered P-pattern style already in
  security-patterns.md (P18, P19, P20, P21, P22).
- **Acceptance:** the patterns file gains 5 new entries, each with a
  one-paragraph "why" + a representative code snippet from this commit.

---

## Done when

- All three items closed; this file moves to `todos/completed/X-cross-cutting.md`.
- The patterns file is the long-term institutional record so future
  sessions don't re-discover these issues.
