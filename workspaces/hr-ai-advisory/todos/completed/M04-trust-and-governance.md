# Milestone 4: Trust, Governance & CARE/EATP

**What users can do after this milestone**: Every piece of advice shows its source, authority level, and confidence. High-stakes queries are clearly flagged with professional referral. The platform has a transparent error correction process. Full EATP audit trail on every advisory response. Users can verify any claim. The platform learns and improves from usage patterns.

**Tasks**: 9

---

## T044: EATP trust lineage implementation

Implement full EATP trust chains using Kaizen's EATP module:

- All domain specialists use `TrustedAgent` (not plain BaseAgent)
- `OrchestratorAgent` uses `TrustedSupervisorAgent` with capability-constrained delegation
- Trust chain per advisory response: User (PseudoAgent) → Orchestrator → Specialist(s) → Response
- Each specialist records: provisions retrieved, reasoning applied, conclusion, confidence score
- `PostgresTrustStore` backed by the same PostgreSQL instance as DataFlow models
- `TrustAwareOrchestrationRuntime` for automatic trust context propagation
- Constraint envelopes: each agent has hard boundaries (TaxAgent cannot advise on employment law, ComplianceAgent cannot make legal determinations)

**Session genesis record** (EATP trust anchor):

- Each advisory session creates a genesis record capturing: user verification level, company profile completeness score at query time, KB currency status per queried domain, agent version hashes
- This becomes the root of the trust chain for that session — enables post-hoc audit to determine whether incorrect responses were due to KB gaps, profile gaps, or agent errors

**Anti-amnesia mechanism** (COC critical pattern):

- Per-turn constraint re-injection: every agent turn re-injects critical rules that survive context window compression
- Re-injected on every turn: (1) "cite only from KB, never from training data," (2) agent's domain constraint envelope, (3) current risk-tier classification rules
- Prevents the most dangerous failure mode: agents drifting from KB citations to parametric memory in long conversations

**Constraint envelope testing**:

- Adversarial test suite: queries designed to make agents exceed their domain (e.g., trick TaxAgent into giving employment law advice)
- Post-generation validation layer: verify every response stays within the agent's constraint envelope (deterministic check, not just prompt instruction)
- Log constraint boundary violations for audit

Every advisory response carries a verifiable trust lineage in the AdvisorySession record.

**Red team fix R2-GAP6**: Genesis record ensures trust lineage starts at the root, not in the middle.
**Red team fix R2-GAP1**: Anti-amnesia mechanism is the single most important COC pattern for a regulatory platform.
**Red team fix R2-REC3**: Constraint envelopes are tested adversarially and enforced deterministically.

---

## T045: Source citation and authority level system

Implement the transparency layer across both frontends:

- Every advisory response includes clickable source citations: "Employment Act, Section 88A"
- Authority level markers on every piece of advice: [STATUTORY], [TRIPARTITE GUIDELINE], [BEST PRACTICE]
- Visual distinction: statutory = solid blue badge, guideline = outlined amber badge, best practice = outlined green badge
- "View source" action: shows the full formal text of the cited provision
- Cross-references: "Related: [CDCSA s9-12] [TAFEP Guidelines on...]"
- Knowledge currency indicator: "This information was last verified on [date]"
- **KB search integration**: users can search provisions directly from the citation panel (by domain, authority level, effective date)

**Pre-delivery citation validation** (hard guardrail, not just a test):

- Every cited provision is checked against the KB before the response is sent to the user
- If a citation cannot be resolved to a current KB provision, the response is blocked and regenerated
- This is a deterministic validation hook, not a probabilistic check — runs on every response

**Red team fix R2-GAP2**: KB search functionality integrated into citation system.
**Red team fix R2-REC2**: Citation validation is a pre-delivery guardrail, not just an audit mechanism.

---

## T046: Risk-tiered disclaimer system

Implement the three-tier disclaimer framework:

- **Platform level**: Terms of service with: HR information and guidance (not legal advice), based on publicly available regulations, recommend professional verification for critical decisions, PI insurance disclosure
- **In-conversation GREEN**: No per-query disclaimer. Source citation is the transparency mechanism.
- **In-conversation AMBER**: Light framing: "Based on current tripartite guidelines..." / "This reflects current best practices."
- **In-conversation RED**: Strong disclosure block (visually distinct, not fine print), immediate obligations, "consider consulting an employment lawyer" recommendation, "connect to specialist" CTA
- Disclaimer is contextual to the risk tier — never a blanket banner undermining the product

**Verification gradient** (operational depth per tier):

- GREEN: automated KB-citation validation only (pre-delivery hook from T045)
- AMBER: citation validation + confidence threshold check + cross-domain consistency validation
- RED: all AMBER checks + response added to human review queue for expert review within 24 hours; response is delivered immediately but flagged for post-delivery audit
- Verification depth logged in trust lineage for each response

Based on the disclaimer/liability framework research (06-disclaimer-liability-framework.md).

**Red team fix R2-GAP3**: Verification gradient specifies concrete operational depth per tier.

---

## T047: Error correction and transparency process

Build the error handling infrastructure:

- Error discovery workflow: when wrong advice is identified (user report, expert audit, regulatory change lag)
- Affected user notification: identify users who received the incorrect advice (via AdvisorySession records), send correction notification via email and in-app alert
- Knowledge base correction: update/supersede the incorrect provision, log the correction
- Transparent error log: publicly accessible page showing corrections made, when, and why
- "This regulation changed on [date]. Our knowledge base was updated on [date]." — if there was a lag, disclose it
- Post-correction audit: verify all related provisions and cross-references are consistent

---

## T048: CARE framework governance integration

Implement CARE principles in the platform's operational governance:

- **Human-on-the-Loop**: Human experts validate all KB updates before publication (built in T040). No AI autonomously updates regulatory content.
- **Dual Plane Model**: Trust Plane (human accountability for content accuracy, boundary definition, escalation rules) vs Execution Plane (AI-scaled delivery of advisory)
- **Constraint envelopes**: hard boundaries per agent (implemented in T044). Agents cannot exceed their domain authority.
- **Verification gradient**: GREEN queries need minimal verification; RED queries trigger enhanced audit trail and optional human review queue (specified in T046)
- **COC five-layer completeness**: ensure institutional knowledge is captured in the KB structure, not just in agent prompts. Agent knowledge must be grounded in the KB, not parametric memory.

**Expert validation workflow** (operational design):

- Reviewer qualifications: IHRP-certified practitioners for employment/HR content, employment lawyers for statutory interpretation, CPF/tax specialists for domain-specific content
- Review SLA: 24 hours for critical (statutory changes), 72 hours for standard updates
- Minimum two independent reviewers for statutory content; one reviewer for best-practice content
- Expert approval recorded in trust store with reviewer identity and timestamp
- Review interface: diff view of provision changes, side-by-side comparison with source material

**Red team fix R2-GAP5**: Expert validation workflow has concrete operational design, not just a checkbox.

---

## T049: Advisory accuracy testing framework

Build the ongoing accuracy assurance system:

- Monthly expert audit: random sample of advisory responses reviewed by IHRP-certified practitioner or employment lawyer (via T041 admin interface)
- Automated regression tests: known-correct answers for 200+ common HR scenarios (the top 10 questions per persona × 4 personas = 40 baseline scenarios, expanded to 200+)
- Hallucination detection: every cited provision must exist in the KB and be currently in force (validation layer in T045)
- Confidence scoring: low-confidence responses flagged for human review
- User feedback loop: thumbs up/down on every response (UI built in T003/T004, stored in T007 UserFeedback model)
- Accuracy dashboard: track accuracy metrics over time, by domain, by risk tier (via T041 admin interface)

---

## T050: Platform learning and feedback loop (COC Layer 5)

Build the learning pipeline that makes institutional knowledge compound over time:

- **Usage pattern analysis**: log query patterns, agent routing decisions, confidence scores, and user feedback
- **KB gap detection**: identify query patterns that consistently produce low-confidence responses — these indicate topics where the KB needs expansion
- **Agent routing optimization**: identify which domain combinations frequently co-occur — inform orchestrator routing improvements
- **Resolution pattern capture**: successful resolution patterns for complex cross-domain queries are logged for future reference
- **Feedback-to-action pipeline**: thumbs-down responses are categorized (wrong answer, outdated info, unclear explanation, missing topic) and fed into KB improvement priorities
- **Periodic recommendations report**: monthly summary of suggested KB expansions, agent prompt refinements, and routing changes — all reviewed by human experts before implementation

All evolved changes go through human review (CARE Human-on-the-Loop). The platform learns, but humans govern what it learns.

**Red team fix R2-GAP4**: COC Layer 5 (Learning) ensures the platform improves over time, not just at launch.

---

## T051: Sector-specific playbooks

Build sector-specific advisory packages for the major SME sectors:

- **F&B**: Foreign worker quotas (services DRC), PWM for cleaning staff, split shift calculations, PH pay for service workers, food hygiene leave considerations
- **Construction**: Higher levies, safety requirements (BCA), dormitory obligations, Safety Orientation Course, WICA coverage specifics
- **Technology**: EP/COMPASS focus, stock option tax treatment, flexible work norms, PDPA obligations for data roles
- **Professional Services**: EP salary thresholds, FCF compliance, non-compete clause advisory
- **Manufacturing**: Factory Act compliance, shift work regulations, noise exposure limits
- **Retail**: Part-time worker management, PH working arrangements, PWM (if applicable)

Each playbook: sector-specific KB provisions + pre-configured applicability rules + sector-relevant suggested questions.

---

## T052: Growth-stage triggers

Build proactive advisory that fires when a company's profile crosses regulatory thresholds:

- 5 employees: "You now have 5+ employees. Here's what changes..."
- 10 employees: AIS submission, enhanced record-keeping
- 25 employees: TAFEP scrutiny increases, FCF requirements for EP hires, retrenchment notification threshold
- 50 employees: WSH Officer requirements (sector-dependent), enhanced MOM reporting
- 100 employees: Enhanced compliance expectations
- First foreign worker hire: DRC explanation, levy obligations, employer responsibilities
- First EP hire: COMPASS requirements, FCF/MyCareersFuture obligations

Triggers fire as alerts when a user updates their company profile past a threshold (using profile change event hooks from T039).
