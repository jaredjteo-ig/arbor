# Gap Resolutions — Red Team Round 1

Addresses findings from `09-redteam-analysis-gaps.md`.

---

## C1: Migration Path (Flat RBAC → PACT)

**Resolution: Parallel systems with feature flag.**

Arbor keeps the existing 4-role RBAC (`owner`, `hr_manager`, `consultant`, `employee`) as the base layer. PACT runs alongside, not replacing it. The migration:

1. **Phase 0 (now)**: Existing RBAC works as-is. No changes to auth middleware.
2. **Phase 1**: Add `PactNode`, `PactEnvelope` models alongside existing models. Add `pact_enabled` company flag (default: false).
3. **Phase 2**: When `pact_enabled=true`, the PACT envelope check runs AFTER the RBAC check. Both must pass. PACT can only tighten, never widen existing permissions.
4. **Phase 3**: For agent-filled roles, the "user" is the agent service account. Its RBAC role is `hr_manager` (existing permission set). Its PACT envelope constrains within that.

**Key principle**: PACT is additive. A company that never enables PACT gets the same Arbor as today. PACT tightens, never replaces.

**Build-now boundary**: Models (PactNode, PactEnvelope) and the `pact_enabled` flag. Engine evaluation comes from `pact` core library.

---

## C2: Held-Action Notification Pipeline

**Resolution: Specify the pipeline now. It's 3 components.**

```
Agent action → Gradient evaluation → Zone = HELD
  → Create HeldAction record (DataFlow model)
  → Trigger notification:
    1. In-app badge (real-time via SSE, existing infrastructure)
    2. Push notification (extend existing push_service.py)
    3. WhatsApp/Telegram (via existing MCP communication server)
  → Boss opens notification → Reviews → Approves/Rejects
  → Agent proceeds or stops
  → EATP audit record created
```

**New DataFlow model**: `HeldAction` (agent_role, action_type, action_details JSON, company_id, status: pending/approved/rejected, reviewer_id, reviewed_at, created_at)

**Notification types to add to push_service.py**:

- `HELD_ACTION` — "Your HR Agent needs approval: Sarah requested leave during notice period"
- `DAILY_DIGEST` — "3 actions need your review today"
- `ESCALATION` — "Held action pending for 48 hours"

**Channel priority**: WhatsApp > Push > Email > In-app (configurable per company).

**This is the #1 implementation priority.** Without it, the governance model is invisible.

---

## C3: Build-Now vs Wait-for-PACT-Core Boundary

**Resolution: Explicit boundary table (following Astra exactly).**

| What                                             | Build Now (Arbor) | Wait For (PACT Core)         |
| ------------------------------------------------ | ----------------- | ---------------------------- |
| Org templates (YAML + dataclass)                 | YES               | —                            |
| Agent role definitions                           | YES               | —                            |
| Clearance classification registry                | YES               | —                            |
| Envelope template definitions                    | YES               | —                            |
| Gradient calibration tables                      | YES               | —                            |
| Bridge definitions                               | YES               | —                            |
| Regulatory mappings                              | YES               | —                            |
| Acceptance tests (assertions against future API) | YES               | —                            |
| HeldAction model + notification pipeline         | YES               | —                            |
| Agent service accounts + RBAC mapping            | YES               | —                            |
| `PactNode`, `PactEnvelope` DataFlow models       | YES (schema)      | Engine populates             |
| `pact_enabled` feature flag                      | YES               | —                            |
| D/T/R address computation                        | —                 | YES (`pact.Address`)         |
| Envelope intersection / monotonic tightening     | —                 | YES (`pact.EnvelopeEngine`)  |
| `can_access()` clearance algorithm               | —                 | YES (`pact.ClearanceEngine`) |
| Gradient evaluation engine                       | —                 | YES (`pact.GradientEngine`)  |
| EATP record generation                           | —                 | YES (`pact.EatpBridge`)      |

**Rule**: Arbor NEVER writes governance engine code. It writes configuration, models, notifications, and acceptance tests. The engine comes from `pip install pact`.

---

## C4: 24-Hour Aha vs Observe-for-Days

**Resolution: The aha moment is NOT the first agent activation. It's the first useful action.**

Timeline reconciled:

- **Hour 1**: Register → add employees → see auto-generated org chart ("Arbor understood my company")
- **Hour 2**: Ask an advisory question → get accurate SG employment law answer with citations ("This actually knows the law")
- **Hour 24**: Morning briefing notification: "2 leave balances running low, 1 work permit expiry in 60 days" ("It's already watching")
- **Day 3-7**: First agent offer: "You've been approving routine leave manually. Want me to handle that?"
- **Day 14**: First agent activation

The 24-hour aha is the **morning briefing** (proactive value from observation), not agent activation. Agent activation is Day 7-14 after trust is built through advisory + briefings.

**User flow 01 updated principle**: Remove "observes for a few days before acting." Replace with "starts delivering value immediately through advisory and briefings; offers agent capabilities after trust is established."

---

## H1: Agent Count (12 vs 6 vs 1)

**Resolution: 12 internal capabilities, 3 user-facing agents, 1 at a time.**

The user sees:

- **Arbor HR** — handles leave, attendance, onboarding, employee queries
- **Arbor Payroll** — handles CPF, payslips, statutory filings, claims
- **Arbor Compliance** — handles regulatory monitoring, filing reminders, audit prep

Internally, each user-facing agent is composed of multiple capability modules (the 12 from the spec). But the boss never sees "12 agents." They see 3, activated one at a time through progressive deployment.

**Mapping**:
| User-Facing | Internal Capabilities |
|---|---|
| Arbor HR | HR Manager, Leave Admin, Attendance, Onboarding, Document, Shadow |
| Arbor Payroll | Payroll, Claims, Reports |
| Arbor Compliance | Compliance, Advisory, Recruitment |

---

## H2: Pricing

**Resolution: Freemium.**

- **Free**: Advisory (unlimited), calculators, compliance dashboard, employee directory. No agents.
- **Starter ($49/month)**: 1 agent (Arbor HR or Arbor Payroll). Up to 10 employees.
- **Growth ($149/month)**: All 3 agents. Up to 50 employees.
- **Custom**: Larger companies, consultant access, API.

Free tier proves value (advisory + briefings). Paid tier activates agent-filled roles. The $49 price point is competitive with HR outsourcing ($500-2000/month) while accessible for micro-SMEs.

---

## H3: Conflicting Envelope Values

**Resolution: Agent envelopes (Section 2 of 05) are the authoritative source. Role templates (Section 4) are the user-friendly presentation. Values must match.**

Action: Reconcile during /todos. The envelope templates define the PACT configuration; the agent capability descriptions describe what the user sees. Both must produce the same effective permissions.
