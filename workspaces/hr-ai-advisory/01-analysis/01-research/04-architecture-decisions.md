# Architecture Decision Records: HR Advisory Platform

---

## ADR-001: AI Approach for Advisory Engine

### Status

Proposed

### Context

The platform's core value is providing accurate, contextualized HR advisory based on Singapore employment law and regulations. The AI approach must balance several competing requirements:

1. **Accuracy is paramount** -- incorrect legal advice has real consequences (fines, lawsuits, employment disputes). The acceptable error rate for factual statements of law is 0%.
2. **Contextual reasoning is required** -- the AI must apply general legal provisions to specific company contexts (sector, size, worker mix, salary levels).
3. **Source citation is mandatory** -- every claim must be traceable to a specific provision in the knowledge base.
4. **Content must stay current** -- Singapore updates employment regulations frequently. The system must reflect changes within 48 hours of gazette publication.
5. **Natural conversation** -- users (especially Persona A: SME owners with no HR background) need to ask questions in plain language and get understandable answers.

### Decision

**Hybrid RAG architecture with structured knowledge base and domain-specific guardrails.**

The system uses a three-layer approach:

**Layer 1: Structured Knowledge Base (the source of truth)**

- All regulatory content stored in a structured, versioned database -- not as unstructured text blobs, but as typed provisions with metadata (Act, section, effective date, applicability rules, supersession chain).
- This is NOT a simple vector store. It is a relational knowledge graph where provisions link to related provisions, applicability rules, and practical examples.
- Every provision has a unique identifier and version history.

**Layer 2: Retrieval-Augmented Generation (RAG)**

- User queries are processed through a retrieval pipeline that:
  1. Analyzes the query to identify relevant domains (e.g., "maternity leave" maps to Domain 4.3, which maps to CDCSA s9-12 and EA s76-80).
  2. Pulls the user's company profile to determine applicability filters (sector, size, worker types).
  3. Retrieves relevant provisions from the structured KB, filtered by applicability.
  4. Passes retrieved provisions plus company context to the LLM for response generation.
- The LLM generates a response that is grounded in the retrieved provisions. It does not answer from parametric memory alone.

**Layer 3: Validation and Guardrails**

- Post-generation validation checks that:
  1. Every cited provision actually exists in the KB (anti-hallucination).
  2. Every cited provision is currently in force (not repealed/superseded).
  3. Applicability rules are respected (e.g., Part IV provisions not cited for employees earning above the threshold).
  4. Confidence scoring based on retrieval quality (if retrieval returns low-relevance results, flag as low confidence).
  5. Escalation triggers fire for high-stakes topics (dismissal disputes, TADM proceedings, etc.).

**Calculator tools are deterministic, not AI-generated.** CPF, levy, quota, and leave calculations use hard-coded rate tables (updated via the content pipeline) with standard arithmetic. The AI may invoke these tools but does not compute the numbers itself.

### Consequences

#### Positive

- **Accuracy**: Every AI claim is grounded in verified KB content. Hallucination risk is minimized by validation layer.
- **Traceability**: Full audit trail from user question to retrieved provisions to generated response.
- **Updatability**: Regulatory changes update the KB, which immediately changes what the AI retrieves. No model retraining needed.
- **Contextual**: Company profile filters ensure advice is relevant to the user's specific situation.
- **Transparent**: Users can see exactly which legal provisions back each piece of advice.

#### Negative

- **Complexity**: Three-layer architecture is more complex than a simple fine-tuned chatbot. More components to build, test, and maintain.
- **Latency**: Retrieval + generation + validation adds latency compared to a single LLM call. Must be optimized to meet the 3-second first-token target.
- **KB dependency**: Advisory quality is bounded by KB completeness. Gaps in the KB mean gaps in advisory (but this is actually safer than hallucinating answers for uncovered areas).
- **Initial KB creation effort**: Building the structured knowledge base is a significant upfront investment (estimated 4-8 weeks for comprehensive coverage of all 18 domains).

### Alternatives Considered

#### Option A: Fine-Tuned Model

- **Description**: Fine-tune an LLM on Singapore employment law corpus. The model "knows" the law and answers from parametric memory.
- **Pros**: Simpler architecture. Potentially lower latency. Can handle nuanced reasoning.
- **Cons**: Catastrophic for accuracy. Cannot cite sources reliably. Cannot be updated without retraining (days-weeks lag for regulatory changes). Hallucination risk is inherent and undetectable. Cannot distinguish between what the model "knows" accurately vs what it confabulates. No audit trail.
- **Why rejected**: The accuracy requirements (0% factual error rate) are incompatible with parametric-memory-only approaches. When the model is wrong, it is wrong confidently and undetectably.

#### Option B: Pure RAG (Unstructured)

- **Description**: Standard RAG with vector store of regulatory documents. Chunk documents, embed, retrieve by similarity, generate.
- **Pros**: Simpler than structured KB. Faster to set up. Well-understood pattern.
- **Cons**: Loses the structured metadata that makes contextual filtering possible. A vector search for "maternity leave" returns chunks that may or may not be relevant to the user's company type. No applicability filtering. Cross-references between provisions are lost. Version tracking is manual. Hallucination harder to detect (retrieved chunks may be tangentially relevant, leading to plausible but wrong synthesis).
- **Why rejected**: Insufficient for the precision needed. Unstructured RAG works well for general knowledge assistants but not for legal advisory where applicability rules, effective dates, and cross-references are critical.

#### Option C: Rule-Based Expert System (No LLM)

- **Description**: Traditional decision-tree / rule-based system. User selects their situation from menus, system walks through a decision tree to the answer.
- **Pros**: 100% deterministic. 100% auditable. No hallucination. Easy to validate.
- **Cons**: Cannot handle natural language. Cannot handle novel question formulations. Cannot reason about complex multi-domain scenarios. Cannot generate documents. User experience is rigid and frustrating. Building decision trees for 18 domains with hundreds of sub-topics is impractical.
- **Why rejected**: Does not meet the natural language Q&A requirement (ADV-001) or the user experience expectations of modern software. Would not serve Persona A (SME owners who do not know legal terminology to navigate menus).

#### Option D: LLM with Retrieval + Fine-Tuning (Hybrid)

- **Description**: Fine-tune on Singapore employment law AND use RAG for grounding.
- **Pros**: Model has stronger priors for the domain. May produce more natural responses. Retrieval catches gaps.
- **Cons**: Retraining cost and lag for updates. Risk that fine-tuned knowledge conflicts with retrieved current information. More complex training pipeline. Model may "know" outdated law from training data and prefer it over retrieved current provisions.
- **Why rejected for MVP**: Added complexity of fine-tuning pipeline without clear benefit over well-structured RAG. Revisit post-launch if response quality from pure RAG is insufficient for complex reasoning tasks.

### Implementation Plan

1. **Phase 1 (Weeks 1-3)**: Build structured KB schema and populate for 3 priority domains (EA, CPF, Foreign Manpower). Build basic retrieval pipeline.
2. **Phase 2 (Weeks 3-5)**: Integrate LLM generation with company profile context. Build validation layer (citation checking, applicability validation).
3. **Phase 3 (Weeks 5-6)**: Build deterministic calculator tools. Integration testing across all three layers.
4. **Phase 4 (Weeks 7-12)**: Expand KB to remaining 15 domains. Tune retrieval quality. Accuracy testing.

---

## ADR-002: Knowledge Base Structure

### Status

Proposed

### Context

The knowledge base is the foundation of the entire platform. It determines the quality ceiling for all advisory, compliance checking, template generation, and calculator accuracy. The structure must support:

1. **Multi-source content**: Acts of Parliament, subsidiary legislation, tripartite guidelines, MOM advisories, CPF circulars -- each with different authority levels and update mechanisms.
2. **Versioning**: Regulations change. The KB must track what was in force at any point in time, not just the current version.
3. **Applicability rules**: Not all provisions apply to all employers. The KB must encode who each provision applies to.
4. **Cross-references**: Singapore employment law is deeply interconnected. Maternity leave involves the CDCSA, EA, CPF Act, and TAFEP guidelines simultaneously.
5. **Retrieval**: Must support both structured queries ("What are the CPF rates for age 55-60 citizens?") and semantic search ("My employee is pregnant, what do I do?").

### Decision

**Graph-structured relational knowledge base with semantic search overlay.**

The KB uses a dual structure:

**Primary: Relational/Graph Store**

```
Provision (core entity):
  - id: unique identifier (e.g., "EA-s14-2")
  - source_act: FK to Act/Guideline
  - section: string (e.g., "s14(2)")
  - title: string
  - formal_text: string (exact legal text)
  - plain_summary: string (plain-language explanation)
  - effective_date: date
  - superseded_date: date (null if current)
  - superseded_by: FK to Provision (null if current)
  - authority_level: enum [statute, subsidiary_legislation, tripartite_guideline, advisory, best_practice]
  - domain: FK to Domain
  - sub_domain: FK to SubDomain

Applicability Rule (who does this provision apply to):
  - provision_id: FK to Provision
  - rule_type: enum [includes, excludes]
  - criteria_type: enum [ea_coverage, salary_threshold, headcount_threshold, sector, citizenship, pass_type, union_status]
  - criteria_value: JSON (flexible value depending on criteria type)
  - notes: string

Cross-Reference (links between provisions):
  - source_provision: FK to Provision
  - target_provision: FK to Provision
  - relationship_type: enum [related, overrides, supplements, conflicts, requires, exempts]
  - notes: string

Practical Example:
  - provision_id: FK to Provision
  - scenario: string
  - calculation: JSON (if applicable)
  - outcome: string

Rate Table (for calculators):
  - table_type: enum [cpf_rate, levy_rate, quota_ratio, leave_entitlement]
  - effective_date: date
  - expiry_date: date
  - criteria: JSON (age tier, citizenship, sector, etc.)
  - rate_value: decimal
  - source_url: string

Act / Guideline (source document):
  - id: unique identifier
  - title: string (e.g., "Employment Act (Cap 91)")
  - short_name: string (e.g., "EA")
  - authority_type: enum [act_of_parliament, subsidiary_legislation, tripartite_guideline, mom_advisory, cpf_circular, tafep_guideline]
  - issuing_body: enum [parliament, mom, cpf_board, tripartite_alliance, tafep, ntuc]
  - current_version_date: date
  - official_url: string
  - full_text: text (for reference)

Domain / SubDomain:
  - id: unique identifier
  - name: string (e.g., "Foreign Manpower")
  - description: string
  - parent_domain: FK (null for top-level domains)
```

**Secondary: Vector Index for Semantic Search**

- All provisions (formal text + plain summary + examples) are embedded into a vector store.
- Semantic search is used for initial query understanding and broad retrieval.
- Results from semantic search are then filtered through applicability rules from the relational store.
- This dual-path approach ensures both: (a) natural language queries find relevant provisions, and (b) applicability context is always respected.

**Content Authority Hierarchy** (displayed to users):

1. **Statute** (Employment Act, CPF Act, etc.) -- "The law requires..."
2. **Subsidiary Legislation** (Regulations under Acts) -- "The regulations require..."
3. **Tripartite Guidelines** -- "Tripartite guidelines recommend..." (with note on enforceability)
4. **Advisory** (MOM/CPF advisories) -- "MOM advises..."
5. **Best Practice** -- "Industry best practice suggests..."

### Consequences

#### Positive

- **Precision**: Applicability rules prevent wrong-context advice at the data level, not just the prompt level.
- **Auditability**: Every piece of advice traces to a specific provision with a known source, effective date, and authority level.
- **Updateability**: Regulatory changes are surgical -- update the specific provision, add a supersession link, update rate tables. No need to re-embed entire documents.
- **Cross-referencing**: The graph structure allows the system to surface related provisions the user did not ask about (proactive flagging, ADV-007).
- **Calculator accuracy**: Rate tables as first-class entities with effective dates ensure calculators always use the correct rates.

#### Negative

- **High initial investment**: Building the structured KB requires domain expertise to decompose legislation into provisions, write applicability rules, and create cross-references. Estimated 6-8 weeks for initial population.
- **Maintenance complexity**: Each regulatory change requires structured updates (provision + applicability rules + cross-references + examples), not just text replacement.
- **Expert dependency**: Initial population and ongoing maintenance requires someone who understands Singapore employment law deeply enough to structure it correctly.

### Alternatives Considered

#### Option A: Document-Centric Vector Store

- **Description**: Store whole documents (Acts, guidelines) as chunks in a vector database. Standard RAG approach.
- **Pros**: Fast to set up. Ingest PDFs directly. Well-supported by existing tools.
- **Cons**: Loses structure. Cannot filter by applicability. Cannot track versions. Cannot power calculators. Cross-references are implicit, not explicit. A chunk about "maternity leave" does not carry metadata about who it applies to.
- **Why rejected**: Insufficient for the contextual personalization and accuracy requirements.

#### Option B: Wiki-Style CMS

- **Description**: Use a content management system (like a wiki) where HR experts maintain pages for each topic.
- **Pros**: Easy for content authors. Low technical barrier. Version history built in.
- **Cons**: Unstructured. Cannot power automated applicability filtering. Cannot drive calculators. Search is keyword-only. Cross-references are manual hyperlinks. Difficult to validate completeness.
- **Why rejected**: Does not support the programmatic features (calculators, compliance checking, context engine) that the platform requires.

#### Option C: Hybrid Document + Structured Metadata

- **Description**: Store documents in a vector store but add a metadata layer with structured tags (domain, applicability, effective date).
- **Pros**: Easier to set up than full graph structure. Gets some benefits of structured data.
- **Cons**: Metadata tagging is flat (cannot express complex applicability rules). Cross-references are still implicit. Rate tables still need separate handling. Metadata quality depends on consistent tagging discipline.
- **Why rejected**: Partial solution. The applicability rules for Singapore employment law are genuinely complex (e.g., "Part IV of the EA applies to employees earning up to $4,500 basic monthly salary who are not managers or executives, OR all employees regardless of salary for certain provisions like public holidays and sick leave"). Flat metadata cannot express this.

### Implementation Plan

1. **Phase 1 (Weeks 1-2)**: Design and implement DB schema. Build ingestion pipeline for structured content entry.
2. **Phase 2 (Weeks 2-4)**: Populate 3 priority domains (EA, CPF, Foreign Manpower) with expert input. Build vector index.
3. **Phase 3 (Weeks 4-6)**: Build retrieval pipeline (semantic search -> applicability filtering -> ranked results). Integration with advisory engine.
4. **Phase 4 (Weeks 7-12)**: Populate remaining 15 domains. Build rate table management. Build cross-reference graph.

---

## ADR-003: Context Engine -- Company Profile-Driven Personalization

### Status

Proposed

### Context

A distinguishing feature of this platform is that advice is personalized to the user's company profile. Singapore employment law is not one-size-fits-all:

- The Employment Act has different provisions for different salary levels (Part IV applies below $4,500).
- Foreign worker quotas and levies vary by sector (services, manufacturing, construction, marine, process) and are calculated against local workforce size.
- CPF contribution rates vary by employee age tier and citizenship status (citizen vs PR, first-year PR vs second-year PR).
- Some tripartite guidelines reference company size thresholds (10, 25, 50 employees).
- Sector-specific regulations exist for construction safety, Progressive Wage Model, etc.

Without a robust context engine, every answer would need to include "it depends on your sector / size / worker mix" caveats, which defeats the purpose of personalized advisory.

### Decision

**Profile-first context engine that injects company context into every advisory interaction.**

**Architecture**:

```
User Query + Company Profile
         |
         v
   [Query Analyzer]
         |
         |--> Identified domains (e.g., CPF, Foreign Manpower)
         |--> Extracted entities (e.g., "WP holder", "age 58", "construction")
         |
         v
   [Context Resolver]
         |
         |--> Company sector: construction
         |--> Headcount: 65 (citizens: 20, PRs: 10, WP: 30, S Pass: 5)
         |--> EA coverage: 60 employees under EA, 5 above threshold
         |--> Quota utilization: WP at 85% of DRC, S Pass at 60%
         |--> Applicable thresholds: 25+ (FCF applies), 50+ (various TG)
         |--> Regulatory calendar: CPF rate change in Jan, PWM update in March
         |
         v
   [Retrieval with Applicability Filter]
         |
         |--> Provisions retrieved with applicability check against company profile
         |--> Provisions that do NOT apply to this company are excluded
         |--> Provisions approaching applicability (threshold proximity) are flagged
         |
         v
   [Response Generation]
         |
         |--> "For your construction company with 65 employees..."
         |--> Specific rates, quotas, obligations for THIS company
         |--> Proactive flags: "Note: you are at 85% of your WP quota. Hiring one more WP holder will put you at 88%."
```

**Context Resolution Rules**:

1. **Sector determines**: DRC ratios, levy tiers, PWM applicability, safety regulations, available pass types.
2. **Headcount determines**: Threshold obligations (FCF at 25+, FWA guidelines at 10+, retrenchment notification at 5+), MOM scrutiny level.
3. **Worker mix determines**: Quota utilization, levy costs, CPF obligations (different for citizens vs PRs vs foreigners).
4. **Salary levels determine**: EA Part IV applicability, CPF OW/AW ceiling interactions.
5. **Age distribution determines**: CPF contribution rates (different age tiers), retirement/re-employment obligations.

**Progressive Profile Completion**:

- Users can start with minimal profile (sector + headcount) and get useful advice immediately.
- The system prompts for additional profile data when it needs it for a specific question (e.g., "To calculate your exact CPF obligations, I need to know the age distribution of your employees").
- Profile completeness score is visible, with explanations of what additional data enables.

**Multi-Entity Support** (for Persona B and D):

- A company can have multiple entities/outlets, each with its own workforce composition.
- Quota and levy calculations are per-entity (per UEN).
- Advisory can be entity-specific or consolidated.
- Persona D (consultant) manages multiple client profiles with strict data isolation.

### Consequences

#### Positive

- **Personalized from first interaction**: Users get advice specific to them, not generic advice with caveats.
- **Proactive value**: Threshold tracking and quota monitoring surface risks the user has not thought to ask about.
- **Reduces cognitive load**: Users do not need to know which regulations apply to them -- the system handles applicability.
- **Enables calculators**: All calculators auto-populate with company profile data, reducing input effort.

#### Negative

- **Onboarding friction**: Users must provide company data before getting full value. Mitigated by progressive completion.
- **Data accuracy dependency**: If the user enters wrong profile data, all personalized advice is wrong. Mitigated by validation prompts and periodic re-confirmation.
- **Maintenance**: Applicability rules must be updated whenever regulations change thresholds or sector definitions.
- **Complexity**: The context resolution layer adds architectural complexity and is a potential source of bugs (wrong applicability filtering = wrong advice).

### Alternatives Considered

#### Option A: No Profile, Always Generic

- **Description**: Provide general advisory without company context. Include all applicable caveats and let the user determine what applies.
- **Pros**: No onboarding friction. Simpler architecture. No data collection concerns.
- **Cons**: Fundamentally undermines the product's value proposition. Every answer becomes "it depends on..." which is what Google search already provides. Does not serve Persona A (who does not know which caveats apply to them).
- **Why rejected**: Defeats the purpose of the product.

#### Option B: Profile as Optional Enhancement

- **Description**: Provide general advisory by default. If user has completed profile, enhance with personalization.
- **Pros**: No onboarding friction. Works without profile. Better with profile.
- **Cons**: Dual-mode responses are harder to maintain and test. Users who do not complete profile get worse advice (which may be the users who need good advice most). Creates a confusing two-tier experience.
- **Why rejected**: Partially adopted -- the "progressive completion" approach allows starting without full profile but strongly encourages completion. However, the system always attempts context resolution with whatever profile data is available.

### Implementation Plan

1. **Phase 1 (Weeks 1-2)**: Company profile data model and CRUD. Sector and headcount-based context resolution.
2. **Phase 2 (Weeks 3-4)**: Applicability rule engine. Integration with KB retrieval pipeline.
3. **Phase 3 (Weeks 5-6)**: Quota dashboard and threshold tracker. Progressive profile completion UX.
4. **Phase 4 (Weeks 7-8)**: Multi-entity support. Consultant multi-client mode.

---

## ADR-004: Content Update Pipeline

### Status

Proposed

### Context

Singapore's employment regulatory landscape changes frequently:

- Parliament passes amendments to the Employment Act, CPF Act, etc.
- MOM issues circulars and advisories (sometimes with immediate effect).
- CPF rates change (usually annually, announced in Budget).
- Tripartite guidelines are issued or revised (FWA guidelines, wrongful dismissal guidelines, etc.).
- New legislation is introduced (Workplace Fairness Legislation anticipated).

The content update SLAs are demanding:

- Legislative changes: within 48 hours of gazette.
- MOM circulars: within 24 hours.
- CPF rate changes: before effective date.
- Tripartite guidelines: within 1 week.

An unreliable update pipeline is an existential risk (RISK-002).

### Decision

**Automated monitoring with human expert review before publication.**

The pipeline has four stages:

**Stage 1: Detection (Automated)**

- **Singapore Statutes Online (SSO)**: Automated check for new/amended Acts. SSO provides an RSS-like mechanism for legislative updates.
- **MOM website**: Automated crawler checks for new circulars, advisories, and changes to pass conditions/levy rates. Key pages monitored: /newsroom/, /employment-practices/, /passes-and-permits/.
- **CPF Board website**: Automated check for rate table changes and new circulars.
- **Government Gazette**: Monitor for Subsidiary Legislation notifications.
- **TAFEP website**: Automated check for new/revised guidelines.
- **Tripartite Alliance**: Monitor for new tripartite standards and guidelines.
- Detection runs on a schedule: MOM/CPF daily, legislation weekly, guidelines weekly.
- Detection produces a "change candidate" with: source URL, summary of what changed, affected domains, urgency classification.

**Stage 2: Triage (Semi-Automated)**

- Change candidates are classified by urgency:
  - **Immediate** (new legislation, rate changes, MOM enforcement changes): SLA 24-48 hours.
  - **Standard** (new/revised guidelines, advisories): SLA 1 week.
  - **Low** (best practice updates, case summaries): SLA 2 weeks.
- Automated classification based on source type and keywords.
- Triage queue reviewed by content team daily.

**Stage 3: Authoring (Human Expert)**

- An HR/legal expert reviews the change and authors the KB update:
  - Creates/updates Provision entries with formal text and plain-language summary.
  - Sets applicability rules.
  - Creates cross-references to related provisions.
  - Updates or creates practical examples.
  - Updates rate tables if applicable.
  - Sets supersession links for replaced provisions.
  - Writes the user-facing alert summary (what changed, who it affects, what to do).
- Expert review is critical -- automated ingestion of legal text without expert interpretation is dangerous.

**Stage 4: Validation and Publication (Automated + Human)**

- Automated checks:
  - All required fields populated.
  - Cross-references resolve to valid provisions.
  - Rate table values pass sanity checks (within expected ranges).
  - Applicability rules are syntactically valid.
  - No broken links to official sources.
- Human sign-off: Content team lead approves publication.
- On publication:
  - KB is updated.
  - Vector index is updated for affected provisions.
  - Staleness flags on affected provisions are cleared.
  - User alerts are queued for affected company profiles.
  - Templates linked to updated provisions are flagged for review.
  - Calculator rate tables are updated (if applicable).

**Staleness Tracking**:

- Every provision has a "last validated" date.
- Provisions not validated within their SLA window are flagged as "potentially stale."
- Stale provisions trigger a visible warning in advisory responses: "Note: this provision was last validated on [date]. It may have been updated."
- Monthly staleness audit ensures no provision goes more than 90 days without validation.

**Pre-Announced Changes** (e.g., Budget announcements):

- When changes are announced but not yet in force, they are added to the KB with a "future effective date."
- Advisory responses mention upcoming changes: "Current CPF rate is X%. From January 1, it will increase to Y%."
- Regulatory calendar surfaces all known upcoming changes filtered by company profile.

### Consequences

#### Positive

- **Timely**: Automated detection ensures no major change goes unnoticed.
- **Accurate**: Human expert review prevents automated misinterpretation of legal text.
- **Traceable**: Full audit trail from source detection through expert review to publication.
- **Proactive**: Users are alerted to changes before they need to ask.
- **Safe**: Staleness tracking prevents silent degradation.

#### Negative

- **Operational cost**: Requires ongoing human expert involvement. Cannot be fully automated.
- **Expert dependency**: Quality depends on the HR/legal expert reviewing changes. Single point of failure if team is small.
- **Latency**: Human review adds time to the pipeline. A 24-hour MOM circular SLA requires near-daily expert availability.
- **Scale challenge**: As the regulatory corpus grows, the volume of changes to monitor and process grows too.

### Alternatives Considered

#### Option A: Fully Automated (AI-Driven) Ingestion

- **Description**: AI reads new regulations and automatically updates the KB without human review.
- **Pros**: Fastest possible update time. No human bottleneck. Scales with volume.
- **Cons**: Unacceptable risk. Legal text interpretation requires domain expertise. Automated misinterpretation could introduce systematic errors. A single wrong applicability rule could give wrong advice to hundreds of users. No legal professional would sign off on this approach.
- **Why rejected**: The stakes are too high for fully automated legal interpretation.

#### Option B: Fully Manual (No Automation)

- **Description**: HR experts manually monitor all sources and author all updates.
- **Pros**: Maximum accuracy (human review at every step). No technology risk.
- **Cons**: Does not scale. Experts cannot monitor 7+ sources daily. Changes will be missed. SLAs will be breached. Expensive to staff.
- **Why rejected**: Monitoring is the bottleneck, not interpretation. Automate the detection, keep humans for interpretation.

#### Option C: Crowdsourced Updates (Community Model)

- **Description**: Allow verified HR practitioners to contribute updates (like a Wikipedia for employment law).
- **Pros**: Scales with community. Multiple reviewers catch errors. Practitioners identify real-world application issues.
- **Cons**: Quality control is extremely difficult for legal content. Conflicting edits. Liability issues. No SME owner wants to rely on crowdsourced legal advice.
- **Why rejected**: Appropriate for best practices but not for legal content where accuracy is paramount.

### Implementation Plan

1. **Phase 1 (Weeks 1-2)**: Build automated monitoring for MOM website and SSO. Basic change detection.
2. **Phase 2 (Weeks 3-4)**: Build authoring interface for KB updates. Workflow for triage and review.
3. **Phase 3 (Weeks 5-6)**: Build validation pipeline and publication workflow. Staleness tracking.
4. **Phase 4 (Weeks 7-8)**: Alert generation and delivery. Regulatory calendar. Template staleness flagging.

---

## ADR-005: Trust and Accuracy Framework

### Status

Proposed

### Context

The platform's entire value proposition rests on trust. Users are making real decisions with real consequences based on the platform's advice. The question is not whether errors will occur (they will, given the complexity) but how to:

1. Minimize error frequency to near zero.
2. Make errors detectable when they occur.
3. Limit the blast radius of errors.
4. Build and maintain user trust over time.
5. Handle the inherent tension between AI-generated content and legal accuracy requirements.

This ADR defines the comprehensive framework for ensuring and communicating advisory quality.

### Decision

**Multi-layer trust framework with transparency, validation, escalation, and continuous monitoring.**

**Layer 1: Prevention (Stop Errors Before They Reach Users)**

| Mechanism                | Description                                                                                                                    | Implementation                                                                               |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------- |
| Grounded generation      | AI only makes claims supported by retrieved KB provisions. Never generates from parametric memory for legal/regulatory claims. | RAG architecture (ADR-001). System prompt constrains model to retrieved context.             |
| Citation validation      | Post-generation check that every cited provision exists in KB and is currently in force.                                       | Automated validation pipeline. Responses failing citation check are blocked and regenerated. |
| Applicability validation | Check that cited provisions apply to the user's company profile.                                                               | Context engine (ADR-003) filters provisions before and after generation.                     |
| Calculator determinism   | All numerical calculations use deterministic code with government-published rate tables. AI does not compute numbers.          | Separate calculator module with hard-coded logic and rate tables from KB (ADR-002).          |
| Rate table validation    | Rate tables are validated against government sources on every update. Checksums detect unauthorized changes.                   | Content pipeline (ADR-004) validation stage.                                                 |

**Layer 2: Transparency (Users Know What They Are Getting)**

| Mechanism               | Description                                                                                                               | Implementation                                                                                                                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Authority level markers | Every piece of advice visually marked as: Statute, Subsidiary Legislation, Tripartite Guideline, Advisory, Best Practice. | UI distinction with consistent color coding and iconography.                                                                                                                                               |
| Source citations        | Every legal/regulatory claim links to the specific provision in the KB, which links to the official source URL.           | Inline citations in advisory responses. Click-through to full provision detail.                                                                                                                            |
| Confidence indicators   | Each response carries a confidence level based on retrieval quality, applicability clarity, and topic complexity.         | Three-tier system: High Confidence (clear provision applies directly), Medium Confidence (provision applies but interpretation required), Low Confidence (ambiguous or novel -- seek professional advice). |
| Currency notices        | Every response shows the date of the regulatory data it is based on.                                                      | Automated timestamp from KB provision "last validated" dates.                                                                                                                                              |
| Distinction enforcement | Platform interpretation is always visually separated from direct quotes of law.                                           | Distinct formatting for: (a) exact legal text quotes, (b) platform's interpretation/summary, (c) best practice recommendations.                                                                            |

**Layer 3: Escalation (Proactive Safety Boundaries)**

| Trigger                    | Action                                                           | Topics                                                                                                                                                           |
| -------------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| High-stakes topic detected | Mandatory disclaimer + "seek professional advice" recommendation | Wrongful dismissal, TADM/ECT proceedings, union negotiations, WICA claims above $X, potential criminal violations (EFMA breaches), retrenchment of 10+ employees |
| Low retrieval confidence   | Flag as uncertain, present what is known, recommend verification | Novel questions, cross-domain questions with conflicting provisions, recently changed areas                                                                      |
| Outside scope              | Clearly state the question is outside the platform's expertise   | Tax planning (beyond employer obligations), immigration law (beyond work passes), commercial/contract law, criminal law                                          |
| Ambiguous law              | Present multiple interpretations with reasoning for each         | Provisions with limited case law, areas where tripartite guidelines and common practice diverge, newly enacted provisions without MOM guidance                   |

**Layer 4: Continuous Monitoring (Catch and Fix Errors Quickly)**

| Mechanism               | Description                                                                                                                         | Frequency                                                                                      |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- |
| User feedback loop      | Every response has a "Was this accurate and helpful?" mechanism. Negative feedback triggers expert review of the specific response. | Per response                                                                                   |
| Expert audit            | Random sample of advisory responses reviewed by qualified HR/legal expert for accuracy.                                             | Weekly: 50 responses. Monthly: 200 responses. Quarterly: comprehensive domain-by-domain audit. |
| Automated regression    | Test suite of known-good question-answer pairs. Run after every KB update to detect regressions.                                    | On every KB update                                                                             |
| Calculator validation   | Automated test against government-published examples (where available).                                                             | On every rate table update                                                                     |
| Hallucination detection | Automated scan of responses for claims not supported by any retrieved KB provision.                                                 | Per response (real-time)                                                                       |
| Comparative analysis    | Compare platform advice against advice from qualified HR consultants on a set of benchmark scenarios.                               | Quarterly                                                                                      |
| Error tracking          | All confirmed errors logged with root cause analysis, impact assessment, and remediation. Published error rate as a trust metric.   | Ongoing                                                                                        |

**Layer 5: Liability Protection (Legal Framework)**

| Mechanism                        | Description                                                                                                                                                                        |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Terms of service                 | Clear limitation of liability. Platform provides "information and guidance" not "legal advice."                                                                                    |
| Per-response disclaimers         | Contextual disclaimers calibrated to topic stakes. Light touch for simple queries (leave entitlements), stronger for complex/high-stakes (termination, retrenchment).              |
| Professional indemnity insurance | Platform operator carries PI insurance as a safety net.                                                                                                                            |
| Audit trail                      | Full record of what the user asked, what was retrieved, what was generated, and what was shown. Enables investigation if a user claims they relied on wrong advice.                |
| Clear escalation language        | When the platform recommends professional advice, it does so with specific guidance: "For this type of matter, consult an employment lawyer" or "Contact TADM for free mediation." |

**Trust Metrics (Public Dashboard -- future)**

| Metric                                                               | Target                                                                     | Measurement   |
| -------------------------------------------------------------------- | -------------------------------------------------------------------------- | ------------- |
| Factual accuracy rate                                                | 100% (for direct statements of law)                                        | Expert audit  |
| Interpretation accuracy rate                                         | Over 98%                                                                   | Expert audit  |
| Average response confidence                                          | Over 85% high-confidence                                                   | Automated     |
| User trust rating                                                    | Over 90% "trustworthy"                                                     | User feedback |
| KB currency (% of provisions validated within SLA)                   | Over 95%                                                                   | Automated     |
| Escalation rate (% of queries triggering "seek professional advice") | 10-15% (too low = under-escalating, too high = platform not useful enough) | Automated     |

### Consequences

#### Positive

- **Builds and maintains trust**: Transparency about what the platform is and is not gives users appropriate calibration.
- **Catches errors**: Multiple detection mechanisms mean errors are unlikely to persist undetected.
- **Limits harm**: Escalation triggers prevent the platform from giving confident advice on high-stakes matters where it should not.
- **Continuous improvement**: Feedback and audit loops drive ongoing accuracy improvements.
- **Defensible**: If a user claims harm from reliance on platform advice, the audit trail, disclaimers, and escalation triggers demonstrate responsible design.

#### Negative

- **Operational cost**: Expert audits, content monitoring, and error investigation require ongoing human investment.
- **User friction**: Disclaimers and escalation recommendations add friction. Some users may find "seek professional advice" recommendations frustrating if they came to the platform to avoid that.
- **Over-escalation risk**: If calibration is too conservative, the platform escalates too often and users perceive it as unhelpful. Must be tuned based on user feedback.
- **Complexity**: Five layers of trust mechanisms is significant architectural and operational overhead.

### Alternatives Considered

#### Option A: Minimal Trust Framework (Disclaimers Only)

- **Description**: Generic "this is not legal advice" disclaimer. No source citations. No confidence indicators. No expert audits.
- **Pros**: Minimal implementation effort. Standard for many AI chatbots.
- **Cons**: Grossly insufficient for a platform providing legal/regulatory advisory. Users will not know when advice is unreliable. No mechanism to detect or correct errors. Platform operator exposed to liability.
- **Why rejected**: Does not meet the accuracy and trust requirements. Irresponsible for this use case.

#### Option B: Maximum Trust Framework (Human-in-the-Loop for Every Response)

- **Description**: Every advisory response is reviewed by a qualified expert before delivery to the user.
- **Pros**: Maximum accuracy. Zero AI hallucination risk (human catches everything).
- **Cons**: Destroys response time (hours instead of seconds). Does not scale. Extremely expensive. Defeats the purpose of an AI platform.
- **Why rejected**: Not viable at scale. The right answer is automated validation for routine matters and human expertise reserved for audits and complex escalations.

### Implementation Plan

1. **Phase 1 (Weeks 1-3)**: Citation validation, basic confidence scoring, per-response disclaimers, authority level markers.
2. **Phase 2 (Weeks 4-6)**: Escalation trigger engine, hallucination detection, user feedback mechanism.
3. **Phase 3 (Weeks 7-9)**: Expert audit workflow and tooling, automated regression test suite, calculator validation suite.
4. **Phase 4 (Weeks 10-12)**: Error tracking and root cause analysis system, trust metrics dashboard, comparative analysis baseline.

---

## ADR Summary Matrix

| ADR     | Decision                                                                                 | Key Trade-off                                       | Risk Mitigated                                                 |
| ------- | ---------------------------------------------------------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------- |
| ADR-001 | Hybrid RAG with structured KB and guardrails                                             | Complexity for accuracy                             | RISK-006 (Hallucination), RISK-001 (Incorrect advice)          |
| ADR-002 | Graph-structured relational KB with semantic overlay                                     | Initial build effort for precision and auditability | RISK-003 (Context misapplication), RISK-001 (Incorrect advice) |
| ADR-003 | Profile-first context engine with progressive completion                                 | Onboarding friction for personalization             | RISK-003 (Context misapplication)                              |
| ADR-004 | Automated monitoring + human expert review pipeline                                      | Operational cost for timeliness and accuracy        | RISK-002 (Outdated content)                                    |
| ADR-005 | Five-layer trust framework (prevention, transparency, escalation, monitoring, liability) | Operational overhead for user trust and safety      | RISK-001, RISK-004 (Over-reliance), RISK-006 (Hallucination)   |

---

## Cross-ADR Dependencies

```
ADR-001 (AI Approach)
    |
    |--> Depends on ADR-002 (KB Structure) for retrieval source
    |--> Depends on ADR-003 (Context Engine) for applicability filtering
    |--> Depends on ADR-005 (Trust Framework) for validation layer
    |
ADR-002 (KB Structure)
    |
    |--> Fed by ADR-004 (Update Pipeline) for content currency
    |--> Consumed by ADR-001 (AI Approach) for retrieval
    |--> Consumed by ADR-003 (Context Engine) for applicability rules
    |
ADR-003 (Context Engine)
    |
    |--> Uses ADR-002 (KB Structure) applicability rules
    |--> Integrates with ADR-001 (AI Approach) retrieval pipeline
    |
ADR-004 (Update Pipeline)
    |
    |--> Feeds ADR-002 (KB Structure) with current content
    |--> Triggers ADR-005 (Trust Framework) staleness checks
    |
ADR-005 (Trust Framework)
    |
    |--> Validates output of ADR-001 (AI Approach)
    |--> Uses ADR-002 (KB Structure) for citation validation
    |--> Monitors ADR-004 (Update Pipeline) for currency
```

---

## Open Questions for Resolution

1. **LLM Provider Selection**: Which LLM to use for generation? Trade-offs between capability, cost, latency, data residency (Singapore requirement), and provider stability. Candidates include Claude (Anthropic), GPT-4 (OpenAI), and self-hosted open models for data residency compliance. This requires a separate ADR once options are evaluated.

2. **Data Residency Implementation**: The PDPA requirement for Singapore data residency may constrain LLM choices. If using a cloud LLM API, must the API processing also occur in Singapore, or only storage? Need legal guidance on PDPA interpretation for AI processing.

3. **Expert Sourcing**: The content pipeline (ADR-004) and trust framework (ADR-005) depend on access to qualified HR/legal experts. Sourcing strategy: in-house hire, contract with IHRP-certified practitioners, partnership with law firm?

4. **Regulatory Monitoring API Availability**: The content pipeline assumes web scraping for most government sources. Need to investigate whether SSO, MOM, or CPF Board offer structured APIs or feeds that would be more reliable.

5. **Consultant Multi-Tenancy Architecture**: ADR-003 mentions multi-client support for Persona D (consultants). The data isolation requirements need a more detailed technical design -- separate database schemas per client, row-level security, or separate instances?

6. **Monetization Model Impact on Architecture**: Subscription tiers may affect feature access (e.g., basic advisory free, calculators and document generation paid, compliance audits enterprise). This affects how the architecture gates features.
