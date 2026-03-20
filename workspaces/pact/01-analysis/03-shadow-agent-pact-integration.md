# Shadow Agent PACT Integration

## How Arbor's Shadow Agent Becomes the PACT Operator

**Status**: Working Draft
**Date**: 2026-03-21
**Companion to**: 01-pact-lite-design.md, 02-auto-inference-algorithms.md

---

## 1. Architecture Overview

### 1.1 Current Shadow Agent Architecture

Arbor's shadow agent is an execution engine with these components:

| Component        | File                   | Purpose                                                               |
| ---------------- | ---------------------- | --------------------------------------------------------------------- |
| IntentClassifier | `intent_classifier.py` | LLM-based classification of user messages into (module, action) pairs |
| ToolRegistry     | `tool_registry.py`     | Maps (module, action) to API endpoints with trust levels              |
| Executor         | `executor.py`          | Async HTTP client that calls APIs with user's JWT                     |
| PaceManager      | `pace.py`              | Preview-Approve-Confirm-Exit loop for write operations                |
| ObservationStore | `observation.py`       | User session behavior tracking (page views, clicks)                   |
| MemoryStore      | `memory.py`            | Distilled user preferences from observations                          |
| NudgeService     | `nudges.py`            | Contextual proactive suggestions per page                             |
| BriefingService  | `briefing.py`          | Morning dashboard intelligence                                        |
| Formatter        | `formatter.py`         | Response formatting with Arbor identity                               |
| EntityResolver   | `entity_resolver.py`   | Maps LLM entities to API parameter names                              |
| WorkflowComposer | `workflow_composer.py` | Expands intents into multi-step PACE workflows                        |

### 1.2 PACT Extension Points

The shadow agent gains four new responsibilities:

```
Existing:                          PACT Extension:

IntentClassifier ─────────────────> + Envelope Check
  "What does the user want?"          "Is this within their envelope?"

PaceManager ──────────────────────> + Gradient Evaluation
  "Preview, Approve, Confirm"         "Auto / Flag / Hold / Block?"

ObservationStore ─────────────────> + PACT Pattern Detection
  "What has the user been doing?"     "Does behavior match envelope?"

NudgeService / BriefingService ───> + PACT Suggestions
  "What should we tell the user?"     "How should governance evolve?"
```

### 1.3 New Components

| Component             | Purpose                                                                   |
| --------------------- | ------------------------------------------------------------------------- |
| PactEngine            | Core PACT tree management, address computation, envelope storage          |
| PactGateway           | Pre-action envelope check + gradient evaluation (intercepts every action) |
| PactInferenceEngine   | Pattern detection from observations, suggestion generation                |
| PactSuggestionManager | Suggestion lifecycle: create, present, confirm, apply                     |

---

## 2. The Observe-Infer-Suggest-Confirm-Enforce Loop

### 2.1 Observation: Extending the Current System

The current `ObservationStore` records page views and simple interactions. PACT extends this to record every shadow agent action with governance context.

**Integration point: ShadowExecutor.execute()**

Before and after every API call, the executor records PACT-enriched observations:

```python
async def execute(self, tool, params, jwt_token, current_user=None):
    # ── PRE-EXECUTION: Record intent + envelope check ──────────
    pact_address = get_user_pact_address(current_user)
    envelope = compute_effective_envelope(pact_address)
    gradient_zone = evaluate_gradient(tool, params, envelope)

    observation = {
        "user_id": current_user["sub"],
        "pact_address": pact_address,
        "module": tool.module,
        "action": tool.action,
        "target_model": infer_target_model(tool),
        "target_clearance": get_model_clearance(infer_target_model(tool)),
        "envelope_result": gradient_zone,  # auto/flagged/held/blocked
    }

    if gradient_zone == "blocked":
        record_pact_observation({**observation, "was_approved": False})
        return blocked_result(tool, envelope)

    if gradient_zone == "held":
        # Route to supervisor for approval (via PACE)
        record_pact_observation({**observation, "was_approved": None})
        return held_result(tool, envelope, pact_address)

    # ── EXECUTION ──────────────────────────────────────────────
    result = await self._execute_http(tool, params, jwt_token)

    # ── POST-EXECUTION: Record outcome ─────────────────────────
    record_pact_observation({
        **observation,
        "was_approved": True,
        "cross_department": is_cross_department(pact_address, tool),
    })

    if gradient_zone == "flagged":
        send_flag_notification(pact_address, tool, params)

    return result
```

### 2.2 Inference: The PactInferenceEngine

The inference engine runs as a background task, not on the hot path. It processes accumulated observations to detect patterns.

**Trigger conditions:**

- Every 24 hours (daily batch)
- When a user accumulates 50+ observations since last inference
- When an admin/owner logs in (fresh suggestions for the morning briefing)

**Process:**

```
Step 1: Load 30-day observation window for all users in the company
Step 2: For each user, run pattern detection (see 02-auto-inference-algorithms.md Section 4.2)
Step 3: Filter patterns by confidence threshold (>= 0.70)
Step 4: Deduplicate against existing pending suggestions
Step 5: Check dismissal history (skip if dismissed 3+ times)
Step 6: Generate PactSuggestion records
Step 7: Queue suggestions for presentation in next briefing or nudge
```

### 2.3 Suggestion: Presenting Governance Recommendations

Suggestions are surfaced through three existing channels:

**Channel 1: Morning Briefing (`briefing.py`)**

Add a "Governance" section to the briefing for owner/hr_manager roles:

```python
def _pact_governance_items(company_id, user_address):
    """Surface pending PACT suggestions in the morning briefing."""
    suggestions = query_pending_suggestions(
        company_id=company_id,
        visible_to=user_address,
        limit=3,
    )

    items = []
    for s in suggestions:
        items.append({
            "id": f"pact-{s.id}",
            "category": "governance",
            "title": s.title,
            "description": s.description,
            "action_type": "pact_suggestion",
            "suggestion_id": s.id,
            "priority": "medium",
        })
    return items
```

**Channel 2: Nudges (`nudges.py`)**

Add PACT nudges to the page-context system. These appear when the user is on a relevant page:

```python
def _nudges_pact(company_id, user_id, user_role):
    """PACT-specific contextual nudges."""
    if user_role not in ("owner", "hr_manager"):
        return []

    nudges = []
    user_address = get_user_pact_address(user_id)
    suggestions = query_pending_suggestions(
        company_id=company_id,
        visible_to=user_address,
        limit=2,
    )

    for s in suggestions:
        nudges.append({
            "id": f"nudge-pact-{s.id}",
            "type": "governance",
            "message": s.description,
            "action_type": "pact_suggestion",
            "suggestion_id": s.id,
            "dismissible": True,
            "priority": 3,  # Lower priority than operational nudges
        })

    return nudges
```

**Channel 3: Shadow Agent Response (conversational)**

When a user interacts with the shadow agent and a relevant suggestion exists:

```
User: "Approve Ah Mei's payroll run for March"
Shadow Agent: "Done — I've approved the March payroll run ($47,200).

By the way, this is the 4th time you've approved Ah Mei's payroll run.
Want me to let her do this directly in the future?
[Yes, give her access] [No, I want to keep approving]"
```

### 2.4 Confirmation: Owner Decision Points

Each suggestion presents exactly three options:

| Option  | Label                                     | Behavior                                                |
| ------- | ----------------------------------------- | ------------------------------------------------------- |
| Accept  | "[action verb]" (e.g., "Give her access") | Apply the proposed change immediately                   |
| Explore | "Tell me more" / "Show me what changes"   | Show details of what will change                        |
| Dismiss | "Not now" / "No thanks"                   | Dismiss; will re-suggest in 14 days if pattern persists |

**Confirmation API endpoint:**

```
POST /pact/suggestions/{suggestion_id}/respond
Body: { "action": "accept" | "dismiss" | "explore" }
Auth: Requires owner or hr_manager role
```

**The "Explore" response shows:**

```
"Here's what would change if you approve this:

BEFORE:
  Ah Mei can: manage leave, manage attendance, view payroll
  Ah Mei cannot: approve payroll runs (needs your OK each time)

AFTER:
  Ah Mei can: manage leave, manage attendance, view payroll,
              approve payroll runs
  Ah Mei cannot: submit CPF, generate IR8A (these still need your OK)

This change is reversible — you can take back this access anytime
from the Settings page."
```

### 2.5 Enforcement: Applying Confirmed Changes

When a suggestion is accepted, the system:

1. **Modifies the PACT structure** (envelope widened, bridge created, clearance upgraded)
2. **Validates monotonic tightening** (the change cannot make any envelope wider than its parent)
3. **Creates EATP audit records** (tamper-evident trail of the governance change)
4. **Creates PactAuditEvent** (internal audit trail)
5. **Notifies affected users** (e.g., "Your manager has updated your permissions. You can now approve payroll runs.")
6. **Updates the shadow agent's observation baseline** (so the pattern detector doesn't re-suggest the same thing)

---

## 3. Suggestion Scripts by Category

### 3.1 Structural Suggestions (D/T/R Changes)

**Trigger: Company grows past 10 employees with 3+ departments**

```
SCRIPT: departmentalization_suggestion

CONDITION:
  employee_count >= 10
  AND unique_departments >= 3
  AND pact_tree has flat structure (all employees under one D-R)

TITLE: "Organize your team structure"

DESCRIPTION:
  "Your team has grown to {count} people across {dept_count} areas:
  {dept_list}. Right now, everyone's access and approvals flow
  through you directly.

  Want me to set up team structures so each area has its own
  approval flow? This means:
  - {dept_head_1} handles {dept_1} approvals
  - {dept_head_2} handles {dept_2} approvals
  - You only see things that need the company owner's attention

  [Set up teams] [Tell me more] [Not now]"

ON_ACCEPT:
  1. Identify department heads (highest seniority per department)
  2. Create D nodes for each department
  3. Move employees under their department heads
  4. Create default envelopes for each department head
  5. Recompute PACT addresses
  6. Create EATP records for the restructuring
```

**Trigger: Employee added with no reporting manager**

```
SCRIPT: reporting_line_suggestion

CONDITION:
  new_employee has no reporting_manager_id
  AND company has more than 2 employees

TITLE: "Set up {employee_name}'s reporting line"

DESCRIPTION:
  "{employee_name} was just added but doesn't have a manager assigned.
  Based on their role ({designation}) and department ({department}),
  they probably report to {inferred_manager}.

  [Yes, {inferred_manager} is their manager]
  [No, choose someone else]
  [Skip for now]"

ON_ACCEPT:
  1. Set reporting_manager_id on Employee
  2. Update PACT tree (add R node under parent)
  3. Assign template envelope based on designation
  4. Recompute addresses
```

### 3.2 Envelope Refinement Suggestions

**Trigger: Repeated held actions that are always approved**

```
SCRIPT: envelope_widen_suggestion

CONDITION:
  action {module}.{action} has been held >= 3 times in 30 days
  AND all holds were approved by supervisor
  AND average approval time < 5 minutes

TITLE: "Streamline {action_description}"

DESCRIPTION:
  "{user_name} {action_past_tense} {count} times this month, and
  you approved each one within {avg_time}. Want to let them
  do this directly?

  This means: {user_name}'s shadow agent can {action_description}
  without waiting for your approval.

  You'll still see a notification each time, and you can take back
  this access anytime.

  [Yes, give them access] [No, I want to keep approving] [Not now]"

ON_ACCEPT:
  1. Add action to the role's envelope allowed_action_types
  2. Set gradient for this action to "flagged" (not "auto" — supervisor
     still gets notified)
  3. Create EATP delegation record
```

**Trigger: Consistently fast auto-approvals suggest the threshold is too cautious**

```
SCRIPT: auto_approval_threshold_suggestion

CONDITION:
  action_type {action} is currently "flagged" or "held"
  AND the supervisor has approved 10+ times in 60 days
  AND no rejections
  AND amount thresholds consistently below the limit

TITLE: "Speed up {action_description} approvals"

DESCRIPTION:
  "Leave requests under {threshold} days are always approved —
  you've approved {count} this month without declining any.

  Want to auto-approve leave under {threshold} days?
  You'll be notified, but your team won't have to wait.

  [Auto-approve short leave] [Tell me more] [Not now]"

ON_ACCEPT:
  1. Update the gradient config for the target action
  2. Move threshold from "held" to "flagged" (auto-execute with notification)
  3. Create EATP audit anchor for the policy change
```

### 3.3 Clearance Adjustment Suggestions

**Trigger: User blocked from accessing data they need for their job**

```
SCRIPT: clearance_upgrade_suggestion

CONDITION:
  user has been blocked from {model} access >= 2 times in 14 days
  AND the access was attempted during normal business hours
  AND the access target is within or adjacent to the user's department

TITLE: "Update {user_name}'s data access"

DESCRIPTION:
  "{user_name} has tried to view {data_description} {count} times but
  doesn't currently have access to this type of data.

  If this is part of their job, you can give them access. This would
  let their shadow agent read {data_description} but not change it.

  [Grant read access] [Grant full access] [Not now]"

ON_ACCEPT:
  1. Upgrade the role's PactClearance.max_clearance if needed
  2. Add data scope to the envelope's data_access.allowed_scopes
  3. If "read access" — add to allowed_scopes with write_permissions excluded
  4. Create EATP capability attestation
```

### 3.4 Approval Flow Optimization Suggestions

**Trigger: Shadow agent observes bottleneck patterns**

```
SCRIPT: approval_bottleneck_suggestion

CONDITION:
  average time from "held" to "approved" > 4 hours
  AND the held action type has > 5 occurrences per month
  AND the approval rate is > 90%

TITLE: "Speed up your approval workflow"

DESCRIPTION:
  "{action_description} requests are waiting an average of
  {avg_wait_time} for approval. Since you approve {approval_rate}%
  of them, you might want to:

  Option A: Auto-approve and notify you (fastest for your team)
  Option B: Give {delegate_name} approval authority (they can review instead)
  Option C: Keep as-is (no change)

  [Auto-approve] [Delegate to {delegate_name}] [Keep as-is]"

ON_ACCEPT (Option A):
  1. Move gradient from "held" to "flagged" for this action type
  2. Create audit record

ON_ACCEPT (Option B):
  1. Widen {delegate_name}'s envelope to include approval authority
  2. Keep gradient as "held" but route to the delegate instead of owner
  3. Create EATP delegation record
```

### 3.5 Compliance Alert Suggestions

**Trigger: Anomalous data access detected**

```
SCRIPT: anomalous_access_alert

CONDITION:
  user accessed > 3x their daily baseline of records
  OR user accessed CONFIDENTIAL data outside their normal scope
  OR user accessed another department's data for the first time

TITLE: "Unusual activity detected"

DESCRIPTION:
  "{user_name} accessed {count} employee records today, compared
  to their usual {baseline_count} per day. This has been logged
  in the audit trail.

  This might be routine (e.g., year-end reporting) or it might
  need a conversation.

  [Noted, this is expected] [Restrict their access] [Ask them about it]"

ON_ACCEPT ("Restrict"):
  1. Tighten the role's envelope rate_limit
  2. Flag future similar patterns as "held" instead of "auto"
  3. Create EATP audit anchor
```

---

## 4. Trust Model: Building Owner Confidence

### 4.1 The Trust Ladder

The shadow agent's PACT suggestions follow a trust progression that mirrors CARE's Evolutionary Trust principle:

**Level 1: Transparency (Week 1-2)**

The shadow agent only reports what it observes. No suggestions yet.

```
Morning Briefing:
"This week: 47 leave requests processed, 12 payroll approvals,
3 new employees added. Everything is running normally."
```

This establishes the baseline: the owner sees that the agent understands their company's activity patterns.

**Level 2: Observation Sharing (Week 2-4)**

The shadow agent shares observations without making suggestions.

```
Morning Briefing:
"I've noticed that Ah Mei handles all leave approvals and you
handle all payroll approvals. 100% of leave requests were
approved. I'll keep tracking and let you know if I see any
ways to streamline."
```

This shows the owner that the agent's observations are accurate before it starts making recommendations.

**Level 3: Low-Stakes Suggestions (Week 3-6)**

First suggestions are low-risk, easily reversible, and clearly beneficial.

```
"Leave requests under 2 days are always approved within minutes.
Want to auto-approve those? This just means your team doesn't
have to wait. You'll still see a notification."
```

The worst case if this suggestion is wrong: a 2-day leave auto-approves that should have been reviewed. Low stakes, easy to reverse.

**Level 4: Medium-Stakes Suggestions (Month 2-3)**

After the owner has accepted several low-stakes suggestions successfully, the shadow agent introduces structural and access changes.

```
"Ah Mei has been your sole payroll processor for 3 months.
Want to give her direct payroll approval authority?"
```

**Level 5: Proactive Governance (Month 4+)**

The shadow agent begins anticipating governance needs.

```
"You're about to hire your 20th employee. At this size, most
Singapore companies separate HR and Finance into distinct teams.
Want me to prepare a proposal for restructuring?"
```

### 4.2 Confidence Scoring

Every suggestion carries a confidence score that determines when it is surfaced:

| Confidence | Threshold             | Suggestion Type                 | Example                                                   |
| ---------- | --------------------- | ------------------------------- | --------------------------------------------------------- |
| 0.90-1.00  | Surface immediately   | Pattern is overwhelmingly clear | "10/10 payroll approvals approved within 1 minute"        |
| 0.80-0.89  | Surface after 7 days  | Pattern is strong               | "8/10 leave approvals auto-approved"                      |
| 0.70-0.79  | Surface after 14 days | Pattern is emerging             | "5/7 cross-department accesses this month"                |
| 0.50-0.69  | Do not surface        | Pattern is weak                 | "2 blocked access attempts" — maybe legitimate, maybe not |
| < 0.50     | Ignore                | Noise                           | Single occurrence, no pattern                             |

### 4.3 Feedback Loop

Every owner response feeds back into the confidence model:

```
Accepted suggestions:
  → Increase confidence weight for similar patterns
  → Reduce wait time for similar future suggestions (faster trust ramp)

Dismissed suggestions:
  → Decrease confidence weight
  → Increase wait time before re-suggesting (14 → 28 → never)
  → After 3 dismissals of the same type, stop suggesting entirely

"Explore" then Accept:
  → Owner needed more info — adjust description length up
  → Still a positive signal for the pattern type

"Explore" then Dismiss:
  → Description was clear but owner disagreed with the suggestion
  → Strong negative signal for this specific pattern
```

### 4.4 Guardrails on Shadow Agent Suggestions

The shadow agent can NEVER:

1. **Apply a change without confirmation.** Every PACT modification requires explicit owner/admin approval.
2. **Suggest widening beyond the parent envelope.** Monotonic tightening is enforced at suggestion generation time, not just at application time.
3. **Suggest removing audit logging.** No suggestion will ever disable PDPA logging, PACT audit events, or EATP records.
4. **Suggest changes to its own observation permissions.** The shadow agent cannot suggest changes that would expand its own access to user data.
5. **Surface suggestions to non-admin users.** PACT governance suggestions are only visible to owner and hr_manager roles.
6. **Make more than 3 suggestions per day.** To avoid suggestion fatigue, the system caps at 3 suggestions per briefing cycle.

---

## 5. Fallback: What Happens If the Owner Ignores Everything

### 5.1 The Ignore Scenario

Boss registers the company. Adds 10 employees. Never reads morning briefings. Never responds to nudges. Dismisses all suggestions.

**What happens:**

Everything still works. Here is why:

**D/T/R tree: Auto-generated and valid.**
The tree was built from employee data at registration. It reflects the actual organizational structure (departments, reporting lines). Even if it is imperfect, it provides:

- Positional addressing for every role
- Containment boundaries for data access
- Audit trail context for every action

**Envelopes: Template-based and sensible.**
Each employee got a template envelope matched to their job title. These templates are designed for Singapore SME roles and are conservative by default. The templates work without any customization.

**Clearances: Auto-classified from PDPA categories.**
Every model has a default classification. Every user has a default clearance based on their role. The defaults ensure:

- Employees can see their own data
- HR can see employee data with PDPA logging
- Nobody accidentally sees salary data they shouldn't see

**Verification gradient: Active with template defaults.**

- Routine actions auto-approve (no friction)
- Government submissions require double-confirm (safety)
- Delete operations require confirmation (protection)
- Cross-department access is logged (audit)

**Shadow agent: Continues observing silently.**
The observation system continues tracking behavior. Patterns accumulate. The system is ready for the day the owner does engage.

### 5.2 Degradation Model

| Feature                 | Without Owner Engagement           | With Owner Engagement                  |
| ----------------------- | ---------------------------------- | -------------------------------------- |
| D/T/R structure         | Auto-generated, possibly imprecise | Confirmed and refined                  |
| Envelopes               | Template defaults                  | Customized to actual work patterns     |
| Clearances              | Role-based defaults                | Individually tuned                     |
| Gradient thresholds     | Template defaults                  | Optimized for actual approval patterns |
| Cross-department access | Blocked until bridge exists        | Bridges created based on suggestions   |
| Approval routing        | Everything goes to owner           | Delegated to appropriate managers      |

The ignored system is functional but not optimized. The engaged system is both functional and efficient.

### 5.3 The "Boss Finally Engages" Scenario

Six months later, Boss hires a new HR manager who asks "Why can't I see the payroll data?" This triggers a conversation where Boss opens the morning briefing for the first time.

The briefing shows:

```
"Welcome back! I've been tracking your team's activity and have some
recommendations to make things run smoother:

1. Ah Mei has been your sole HR person for 6 months. She's been
   handling payroll approvals through you 24 times — want to give
   her direct access?

2. Your new HR manager needs access to employee salary data to do
   their job. Want me to set that up?

3. Your Operations team has grown to 8 people with no formal
   team lead. Want to designate John as the team supervisor?

[Review all suggestions] [Set up the basics] [I'll look later]"
```

The "Set up the basics" option applies the top 3 most-confident suggestions in one batch, with a confirmation screen showing all changes.

---

## 6. EATP Integration for PACT Events

### 6.1 Record Types

Every PACT governance action creates an EATP record:

| PACT Event                  | EATP Record Type                        | Content                             |
| --------------------------- | --------------------------------------- | ----------------------------------- |
| Tree compiled               | Delegation Record                       | Organization structure snapshot     |
| Envelope created            | Delegation Record                       | Five-dimensional constraints        |
| Envelope widened            | Delegation Record (supersedes previous) | Updated constraints + change reason |
| Clearance granted           | Capability Attestation                  | Clearance level + compartments      |
| Suggestion accepted         | Audit Anchor                            | Suggestion details + owner decision |
| Suggestion dismissed        | Audit Anchor                            | Dismissal record                    |
| Gradient decision (held)    | Audit Anchor                            | What was held, why, human decision  |
| Gradient decision (blocked) | Audit Anchor                            | What was blocked, why               |
| Bridge created              | Delegation Record                       | Cross-department access grant       |
| Emergency bypass            | Audit Anchor                            | Bypass justification + expiry       |

### 6.2 Audit Trail Completeness

Every action in the system creates at minimum:

1. **ObservationStore entry** — behavioral record (in-memory, TTL-based)
2. **PactAuditEvent** — governance context (persistent, DataFlow model)
3. **PdpaAccessLog** (if accessing CONFIDENTIAL+ data) — regulatory compliance
4. **EATP record** (for governance changes only) — tamper-evident trail

This four-layer audit ensures that:

- Behavioral patterns are available for inference (ObservationStore)
- Governance decisions are permanently recorded (PactAuditEvent)
- PDPA compliance is maintained (PdpaAccessLog)
- Trust is cryptographically verifiable (EATP)

---

## 7. Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Models:**

- Add PactNode, PactEnvelope, PactClearance, PactSuggestion, PactAuditEvent to `company_user.py`
- Add MODEL_CLEARANCE_REGISTRY to a new `pact_registry.py` module

**Tree Builder:**

- Implement `build_pact_tree(company_id)` algorithm
- Integrate with `seed_company_defaults()` — call after employees exist
- Handle incremental updates (employee added/removed/transferred)

**Template Library:**

- Define 12 template envelopes as YAML/dict configurations
- Implement `match_envelope_template(employee, user)` algorithm
- Implement monotonic tightening validation

**Tests:**

- Tree builder with various org structures (flat, hierarchical, mixed)
- Template matching with SG job title corpus
- Tightening validation edge cases

### Phase 2: Enforcement Layer (Week 3-4)

**PactGateway:**

- Pre-action envelope check in ShadowExecutor
- Gradient evaluation (auto/flagged/held/blocked)
- Integration with PACE for held actions
- Blocked action UX copy

**Auth Extension:**

- Add pact_address to JWT payload or session context
- Clearance lookup on request

**Observation Extension:**

- Extend ObservationStore schema with PACT fields
- Record envelope_result on every action

**Tests:**

- Envelope enforcement for all 12 templates
- Gradient evaluation with boundary conditions
- Blocked action response formatting

### Phase 3: Inference and Suggestions (Week 5-6)

**PactInferenceEngine:**

- Pattern detection algorithms (5 pattern types)
- Confidence scoring
- Suggestion generation with deduplication

**PactSuggestionManager:**

- Suggestion lifecycle (pending/accepted/dismissed/expired)
- Dismissal tracking (3-strike rule)
- Batch acceptance for "Set up the basics" flow

**Integration with Briefing/Nudges:**

- Add governance section to morning briefing
- Add PACT nudges to nudge service
- Conversational suggestion in shadow agent responses

**Tests:**

- Pattern detection with synthetic observation data
- Suggestion generation with various confidence levels
- Suggestion application and EATP record creation

### Phase 4: EATP Integration (Week 7-8)

**EATP Records:**

- Delegation Records for envelopes and bridges
- Capability Attestations for clearances
- Audit Anchors for gradient decisions and suggestions

**Audit Trail:**

- PactAuditEvent creation for all governance changes
- Integration with existing PDPA logging

**Tests:**

- EATP record creation for all event types
- Audit trail completeness verification
- Tamper detection for modified records

---

## 8. API Surface

### 8.1 New Endpoints

```
# ── PACT Tree ───────────────────────────────────────────────────
GET    /pact/tree                    # View current D/T/R tree (owner/hr_manager)
POST   /pact/tree/recompute         # Force tree recomputation (owner only)

# ── Envelopes ───────────────────────────────────────────────────
GET    /pact/envelopes               # List all envelopes (owner/hr_manager)
GET    /pact/envelopes/{address}     # View envelope for a specific role
GET    /pact/envelopes/me            # View your own effective envelope

# ── Suggestions ─────────────────────────────────────────────────
GET    /pact/suggestions             # List pending suggestions (owner/hr_manager)
POST   /pact/suggestions/{id}/respond  # Accept/dismiss a suggestion
POST   /pact/suggestions/batch       # Accept multiple suggestions at once

# ── Audit ───────────────────────────────────────────────────────
GET    /pact/audit                   # View PACT audit events (owner/hr_manager)
GET    /pact/audit/{address}         # View audit events for a specific role

# ── Diagnostics (owner only) ────────────────────────────────────
GET    /pact/diagnostics/clearance   # View model clearance registry
GET    /pact/diagnostics/patterns    # View detected patterns (before suggestion)
```

### 8.2 Shadow Agent Extensions

The shadow agent's tool registry gets new PACT tools:

```python
# Added to ToolRegistry._register_core_tools()

self.register(ToolDefinition(
    module="pact",
    action="my_permissions",
    method="GET",
    path="/pact/envelopes/me",
    params=[],
    trust_level="autonomous",
    description="View what you can do in the system",
))

self.register(ToolDefinition(
    module="pact",
    action="team_structure",
    method="GET",
    path="/pact/tree",
    params=[],
    trust_level="autonomous",
    description="View team structure and reporting lines",
))

self.register(ToolDefinition(
    module="pact",
    action="review_suggestions",
    method="GET",
    path="/pact/suggestions",
    params=[],
    trust_level="autonomous",
    description="Review pending governance suggestions",
))
```

This means users can ask the shadow agent:

- "What can I do in the system?" (maps to pact.my_permissions)
- "Show me the team structure" (maps to pact.team_structure)
- "Any governance suggestions?" (maps to pact.review_suggestions)

---

## 9. Privacy and Security Considerations

### 9.1 Observation Data Sensitivity

The extended observation data (PACT context) is itself RESTRICTED clearance. Only the owner and hr_manager can view aggregate observation patterns. Individual users can view their own observation history.

### 9.2 Suggestion Content

Suggestions describe user behavior in aggregate ("Ah Mei approved payroll 4 times"). They do not expose specific data values ("Ah Mei approved $47,200 for John's salary"). The shadow agent's suggestions are designed to be safe for the owner to see on a shared screen.

### 9.3 Envelope Data

Envelope configurations are RESTRICTED. Only the owner, hr_manager, and the employee themselves can view an envelope. Employees see a simplified version ("You can: apply leave, clock in/out, view your payslips. You cannot: access other employees' data.").

### 9.4 EATP Records

EATP records for PACT events are CONFIDENTIAL. They contain the full audit trail of governance decisions, including who approved what and when. Only the owner and roles with CONFIDENTIAL clearance can access the EATP governance trail.
