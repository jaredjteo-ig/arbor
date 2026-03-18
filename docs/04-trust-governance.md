# Trust and Governance Framework

Arbor implements three complementary governance frameworks to ensure advisory responses are accurate, auditable, and safe.

## EATP Trust Lineage

The Enterprise AI Trust Protocol (EATP) provides a complete audit trail for every advisory response. Each response carries a **trust chain** that records exactly what happened, which agents contributed, and what evidence was used.

### Trust Chain Structure

```
GenesisRecord (trust anchor)
    |
    +-- AgentAttestation (orchestrator)
    |
    +-- AgentAttestation (specialist 1)
    |
    +-- AgentAttestation (specialist 2)
    |
    = TrustChain (aggregate)
```

### GenesisRecord

Created at the start of every advisory session. Captures the state of the system at query time:

| Field                          | Purpose                                             |
| ------------------------------ | --------------------------------------------------- |
| `session_id`                   | Unique identifier for this advisory session         |
| `user_verification_level`      | Trust level of the user (verified/standard/limited) |
| `company_profile_completeness` | 0.0-1.0 score of company profile data quality       |
| `kb_currency_status`           | Per-domain last-updated dates                       |
| `agent_version_hashes`         | Versions of all agents involved                     |
| `query_text`                   | The original query                                  |
| `query_domains`                | Detected regulatory domains                         |
| `fingerprint`                  | SHA-256 hash for tamper detection                   |

This enables post-hoc audit: if an incorrect response is later identified, the genesis record shows whether it was caused by a KB gap, a profile gap, or an agent error.

### AgentAttestation

Each agent that contributes to a response records an attestation:

| Field                    | Purpose                                  |
| ------------------------ | ---------------------------------------- |
| `agent_id`               | Which agent produced this output         |
| `agent_role`             | Role (orchestrator/specialist/validator) |
| `agent_version`          | Version hash for reproducibility         |
| `domain`                 | Domains addressed                        |
| `provisions_retrieved`   | Which KB provisions were cited           |
| `reasoning_summary`      | How the agent reached its conclusion     |
| `conclusion`             | The agent's output (truncated)           |
| `confidence_score`       | Self-assessed confidence (0.0-1.0)       |
| `constraint_envelope_id` | Which constraint envelope applied        |
| `constraint_violations`  | Any boundary violations detected         |

### TrustChain

Aggregates the genesis record and all attestations:

- **Chain confidence**: Minimum confidence across all attestations (weakest-link model)
- **Verification depth**: green/amber/red based on aggregate risk
- **Human review flag**: Set when confidence falls below threshold
- **All provisions cited**: Deduplicated list across all agents

The trust chain is included in every advisory response and streaming completion event.

## Constraint Envelopes

Every specialist agent operates within a **constraint envelope** -- hard boundaries defining what it can and cannot do.

```python
ConstraintEnvelope(
    agent_id="cpf_specialist",
    allowed_domains=["cpf"],
    forbidden_domains=["employment_act", "foreign_manpower", "tax"],
    can_make_legal_determinations=False,
    can_modify_kb=False,
)
```

Before a response is returned, `validate_constraint_envelope()` checks that the agent's output stays within its boundaries. Violations are recorded in the trust chain.

## Anti-Amnesia Mechanism

In long conversations, LLMs tend to drift from KB citations to parametric memory. The anti-amnesia mechanism prevents this by re-injecting constraints at every agent turn:

```
[CONSTRAINT 1] Cite ONLY from the knowledge base. NEVER use training data for regulatory claims.
[CONSTRAINT 2] Stay within your domain constraint envelope.
[CONSTRAINT 3] Risk tier classification -- GREEN: informational, AMBER: careful consideration, RED: professional verification.
[CONSTRAINT 4] If confidence is below 0.5, recommend consulting an employment law specialist.
[CONSTRAINT 5] YOUR AUTHORIZED DOMAINS: cpf. DO NOT advise on: employment_act, foreign_manpower, tax.
```

This injection happens for every query, not just the first -- ensuring constraints survive context window compression.

## CARE Governance

The Compliance, Accountability, Responsibility, and Ethics (CARE) framework defines the human-AI boundary using a dual-plane model.

### Dual Plane Model

**Trust Plane** (human accountability):

- Content accuracy validation
- Boundary definition for agents
- Escalation rule governance
- KB update approval
- Error correction verification
- Monthly accuracy audit

**Operators**: IHRP-certified practitioners, employment lawyers, domain specialists (CPF, tax, WSH)

**Execution Plane** (AI-scaled delivery):

- Advisory response generation
- Query classification and routing
- Calculator computation
- Document generation
- Citation validation
- Rate limiting and guardrails

**Constraints on AI**: Cannot modify KB content, cannot make legal determinations, must cite from KB only, must respect constraint envelopes, must flag low-confidence responses.

### Expert Review Workflow

All KB content changes require expert review with qualified reviewers:

| Content Type  | Min Reviewers | Required Qualifications            | SLA      |
| ------------- | ------------- | ---------------------------------- | -------- |
| Statutory     | 2             | IHRP-certified + Employment lawyer | 24 hours |
| Best practice | 1             | IHRP-certified                     | 72 hours |
| Rate table    | 2             | CPF specialist                     | 24 hours |
| Template      | 1             | Domain expert                      | 7 days   |

### Reviewer Qualifications

- `IHRP_CERTIFIED` -- Institute for Human Resource Professionals certification
- `EMPLOYMENT_LAWYER` -- Practising employment lawyer
- `CPF_SPECIALIST` -- CPF domain expertise
- `TAX_SPECIALIST` -- Tax/IRAS domain expertise
- `WSH_SPECIALIST` -- Workplace safety and health expertise
- `DOMAIN_EXPERT` -- General domain expertise

## COC Five-Layer Compliance

The COC (Cognitive Orchestration for Codegen) architecture provides five layers of enforcement during development:

1. **Intent** -- 30 specialized agents route work to the right handler
2. **Context** -- 28 skill directories with 100+ files provide domain knowledge
3. **Guardrails** -- 9 rules + 9 hooks enforce behavioral constraints
4. **Instructions** -- CLAUDE.md + 20 slash commands set priorities
5. **Learning** -- Observation-instinct-evolution pipeline improves over sessions

Critical rules have 5-8 independent enforcement layers. This redundancy ensures that if any four layers fail, the fifth catches the violation.

## Risk Tiering

Every advisory response receives a risk tier:

| Tier  | Meaning                                | Disclaimer                                |
| ----- | -------------------------------------- | ----------------------------------------- |
| Green | Informational, high confidence         | Standard informational disclaimer         |
| Amber | Requires careful consideration         | Enhanced disclaimer with caveats          |
| Red   | High stakes, professional verification | Strong disclaimer + professional referral |

Risk tier is escalated (never downgraded) based on:

- Domain classification (fair employment and foreign manpower default to amber)
- Confidence score (below 0.7 = amber, below 0.5 = red)
- Confidence escalation check (low confidence forces red)
- Response screening failure (forces red)

## Citation Validation

Every advisory response validates its citations against the knowledge base:

1. Provisions are looked up by ID from the KB
2. Each citation is checked for: existence, currency, authority level
3. Warnings are generated for missing or stale citations
4. Citation validity affects the overall confidence score

The `CitationResult` includes validated citations, warnings, and an `is_valid` flag that directly influences the response confidence (0.85 if valid, 0.6 if not).

## Learning Pipeline

The learning pipeline closes the feedback loop between user experience and KB quality:

1. **Feedback recording** -- Users submit thumbs-up/down with optional categorisation
2. **KB gap detection** -- Identifies domains where queries consistently receive low confidence
3. **Improvement recommendations** -- Proposes KB additions, updates, or new provisions
4. **Query pattern tracking** -- Records frequency, confidence, and satisfaction by domain
5. **Monthly reports** -- Aggregates feedback, gaps, and recommendations for expert review

Recommendations follow a human-on-the-loop workflow: `proposed` -> `under_review` -> `approved` -> `implemented` (or `rejected`). Only users with `owner` or `hr_manager` role can approve or apply recommendations.
