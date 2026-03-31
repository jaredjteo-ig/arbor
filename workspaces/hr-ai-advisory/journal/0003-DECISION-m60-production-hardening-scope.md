---
type: DECISION
date: 2026-03-31
created_at: 2026-03-31T16:30:00+08:00
author: co-authored
session_id: arbor-session-10
session_turn: 15
project: arbor
topic: M60 scope — production hardening over new features
phase: todos
tags: [scope, milestone, production, dead-code, testing]
---

# M60: Production Hardening Over New Features

## Decision

M60 focuses exclusively on closing post-migration gaps: dead code deletion (PatchRunner, HRIS API stub), test infrastructure fixes, SDK alignment (version pins, COC sync), and deployment hygiene. No new features.

## Alternatives Considered

1. **Start BYOK implementation** — Deferred. Requires pipeline refactoring and a new DB model. Not blocking users today since server key works.
2. **Start PACT governance integration** — Blocked on pact-core package. Trust levels work via frozensets for now.
3. **Full HRIS API integrations** — Deferred. Requires partnership agreements with providers. CSV import covers the use case.
4. **Redesign PatchRunner for Delegate** — Decided to delete rather than redesign. The adversarial runner is independent and still works. Instruction patching can be rebuilt when needed.

## Rationale

The Delegate migration (last session) left 540 lines of dead PatchRunner code, a misleading docstring, and uncommitted SDK pins. The 37 integration test failures create noise and hide real bugs. These are hygiene debts that compound if left. Closing them first gives a clean baseline for the next feature sprint.

## Consequences

- PatchRunner deleted — no automated instruction patch testing until rebuilt for Delegate
- Integration tests either fixed or properly marked — CI runs clean
- SDK pins committed — reproducible builds
- Production deploy template — next deploy is documented

## For Discussion

1. The PatchRunner deletion trades automated instruction testing for a clean codebase. If advisory quality regresses, what's the detection mechanism without PatchRunner — manual red team queries only?
2. If the 37 integration tests turn out to include code bugs (not just missing Postgres), would that change the priority of this milestone vs BYOK?
3. The old todo roadmap (M61-M65 shadow execution) was archived as completed. Does the project need a new feature roadmap beyond M60, or is Arbor in maintenance mode?
