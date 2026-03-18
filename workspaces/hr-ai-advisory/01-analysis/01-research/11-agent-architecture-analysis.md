# Arbor HR Advisory Agent Architecture Analysis

**Date**: 2026-03-12
**Scope**: Full Kaizen agent pipeline, system prompts, knowledge base, trust layer, and supporting workflows
**Status**: Research complete

---

## Table of Contents

1. [Current Architecture Assessment](#1-current-architecture-assessment)
2. [Recommended Agent/Skills Structure](#2-recommended-agentskills-structure)
3. [System Prompt Optimization Guide](#3-system-prompt-optimization-guide)
4. [Quality Rubric](#4-quality-rubric)
5. [Self-Improvement Architecture](#5-self-improvement-architecture)

---

## 1. Current Architecture Assessment

### 1.1 Architecture Overview

The Arbor HR Advisory platform uses a three-stage Kaizen multi-agent pipeline:

```
User Query
    |
    v
[QueryAnalyzerAgent] -- classifies domain, extracts entities, assigns risk tier
    |
    v
[OrchestratorAgent] -- selects specialists, plans dispatch (parallel/sequential/router)
    |
    v
[Specialist Agents x7] -- domain-scoped advisory with citation requirements
    |
    v
[ComplianceAgent] -- cross-domain consistency check (quality gate)
    |
    v
[ResponseSynthesizerAgent] -- merges specialist outputs into plain-language response
    |
    v
Final Response (with citations, disclaimers, risk tier)
```

Supporting infrastructure:

- **SharedMemoryPool**: Kaizen SharedMemoryPool wrapped with HR-specific metadata validation
- **ShortTermMemory**: Per-session conversation buffer (configurable turn window, default 20)
- **LongTermMemory**: Per-company topic tracking and advisory history (in-memory, designed for DataFlow backend)
- **Knowledge Base**: DataFlow-backed provisions with pgvector embeddings, validation pipeline, bulk loading
- **Trust Layer**: EATP lineage (genesis records, agent attestations, constraint envelopes), CARE governance (dual-plane model, expert review SLAs), citation validation, risk-tiered disclaimers
- **Guardrails**: Query screening (circumvention detection, escalation triggers), response content filtering, rate limiting
- **Singlish Understanding**: Phrase mappings and system prompt additions for Singapore colloquial English
- **Deterministic Calculators**: CPF, leave, salary (proration/overtime), quota/levy -- no LLM involvement
- **Document Generation Agent**: LLM-powered HR document creation from templates
- **Workflows**: Emergency responses, sector playbooks, growth triggers, compliance checker, regulatory update management, employee classification

### 1.2 What Works Well

**1. Clean separation of concerns**. The pipeline stages are well-defined: classification is isolated from advisory, advisory is isolated from synthesis. This prevents scope creep within individual agents and makes each stage independently testable.

**2. Constraint envelopes are explicit**. Every specialist agent has a formally defined constraint envelope in `eatp_lineage.py` specifying allowed and forbidden domains. The anti-amnesia mechanism re-injects these constraints per turn. This is a strong design for regulatory advisory where domain bleeding is dangerous.

**3. Risk-tiered trust architecture**. The three-tier system (green/amber/red) flows through every layer -- from query classification through specialist output to final response synthesis. Disclaimers are enforced programmatically, not left to LLM discretion. The verification gradient applies progressively deeper checks at higher risk tiers.

**4. Deterministic calculators for numerical work**. CPF rates, leave entitlements, overtime pay, and quota/levy calculations are implemented as pure arithmetic functions. The CalculatorAgent contains no LLM at all. This eliminates the hallucination risk for the most error-sensitive outputs.

**5. Citation validation is a hard gate**. The `citation_validator.py` runs as a pre-delivery check against a known provision registry. Citations are either valid or rejected -- there is no "probably valid" category. This is appropriate for regulatory advisory.

**6. Singlish handling is thoughtful**. The phrase mapping table covers real Singapore HR vocabulary ("kena MOM inspection," "resign already," "need pay or not"). The system prompt instructs agents to understand Singlish input without correcting users, and to respond in clear standard English. This is the right tone for Singapore SME users.

**7. Emergency response system is structured and actionable**. The six emergency response types (TADM claim, workplace injury, wrongful dismissal, MOM inspection, discrimination complaint, data breach) each provide immediate obligations with deadlines, required documents, step-by-step processes, escalation triggers, and provision references. This is exactly what an SME owner needs during a crisis.

**8. Sector playbooks provide personalized context**. Six sector-specific packages (F&B, Construction, Technology, Professional Services, Manufacturing, Retail) each contain tailored regulatory provisions, common compliance challenges, and suggested questions in natural language. This allows the system to frontload relevant context.

**9. Growth trigger system is proactive**. Threshold-based alerts (5, 10, 25, 50, 100 employees; first foreign worker; first EP holder) fire when company profiles cross regulatory boundaries. Each trigger includes specific obligations, provision references, and suggested advisory queries.

**10. Signatures follow Kaizen best practices**. All agents use proper `InputField`/`OutputField` declarations with descriptions, defaults, and intent/guidelines annotations. The base specialist pattern allows code reuse while maintaining domain-specific system prompts.

### 1.3 Weaknesses and Gaps

#### Architecture Weaknesses

**W1. The Orchestrator is an unnecessary LLM call**. The OrchestratorAgent receives the QueryAnalyzer's structured output (which already contains domains and routing decisions) and produces a dispatch plan -- essentially reprocessing the same routing decision with an LLM. Its fallback method `_fallback_plan()` shows that deterministic routing from the analysis output is straightforward. This LLM call adds latency and cost without meaningful additional reasoning.

**W2. Knowledge base retrieval is not integrated into the specialist dispatch path**. The `BaseDomainSpecialist.advise()` method accepts `relevant_provisions` as an optional parameter, but nothing in `create_orchestration_pipeline()` or the orchestration agents actually fetches provisions from the KB and passes them to specialists. The pipeline factory creates agents and memory pools but does not wire KB retrieval. This means specialists are currently advising without grounded provisions unless the caller manually retrieves and injects them.

**W3. Conversation history is accepted but not injected into specialist or synthesis prompts**. The `QueryAnalyzerAgent` accepts `conversation_history` and its system prompt mentions using it for context resolution. However, the specialist agents and response synthesizer have no `conversation_history` input field in their signatures, and the pipeline factory does not pass conversation context through. Multi-turn advisory coherence depends on this.

**W4. The ComplianceAgent is optional and not integrated into the pipeline flow**. The `create_orchestration_pipeline()` function does not create a ComplianceAgent instance. The compliance check is architecturally designed to run after specialists but before synthesis, yet this is not wired. If compliance checking is skipped, cross-domain contradictions pass through uncaught.

**W5. Company context is not enriched from LongTermMemory**. The pipeline creates both `ShortTermMemory` and `LongTermMemory` instances, but neither is wired into the agent calls. Previous advisory patterns, frequently asked topics, and stored company profiles in LongTermMemory are not used to enrich the query context. Each session starts from scratch.

**W6. No feedback loop from synthesis back to the trust layer**. The trust infrastructure (EATP lineage, CARE governance) is fully designed but not called during the advisory pipeline. No genesis records are created, no attestations are recorded, and no constraint envelope validation occurs during actual query processing. The trust layer exists as standalone modules.

**W7. Anti-amnesia injection is defined but never called**. The `get_anti_amnesia_injection()` function generates constraint re-injection text that should be prepended to every agent turn to prevent drift from KB citations to parametric memory. However, no agent's `_generate_system_prompt()` method calls this function. In long conversations, specialists may drift toward training data rather than KB provisions.

**W8. Citation validator uses a hardcoded in-memory registry**. The `_KB_PROVISIONS` dict in `citation_validator.py` is a static Python dictionary with approximately 25 entries. In production, this should query the DataFlow knowledge base. The current implementation means new provisions loaded through the KB pipeline are not automatically available for citation validation.

**W9. Rate table data is embedded in calculator code, not sourced from KB**. CPF rates, OW/AW ceilings, and other numerical thresholds are hardcoded in `calculator.py`. When rates change (CPF rates change periodically), both the calculator code and the KB content would need separate manual updates. There is no single source of truth.

**W10. No Data Protection (PDPA) specialist agent**. The system has PDPA provisions in the citation registry, emergency response guidance for data breaches, and PDPA-related compliance challenges in the technology sector playbook. But there is no dedicated PDPA specialist agent. PDPA queries would fall to "general" or be partially handled by the fair employment agent.

**W11. No dedicated "general HR" specialist**. The domain mapping includes `"general": "general_hr_specialist"` in the orchestrator, but no GeneralHRAgent exists. Queries that don't map to a specific regulatory domain have no handler.

**W12. Error handling defaults silently to lowest-risk outputs**. When the LLM returns malformed JSON or unexpected values, every agent defaults to `"green"` risk tier, `0.5` confidence, and generic fallback text. For a regulatory advisory system, silent degradation to "everything is fine" is the wrong failure mode. The system should escalate uncertainty, not suppress it.

#### System Prompt Weaknesses

**W13. Specialist prompts are structurally identical and domain-generic**. Each specialist's system prompt follows the same template: domain constraint, expertise list, citation rules, output format. The expertise lists are high-level topic summaries (e.g., "Part IV protections (rest days, hours of work, overtime, holidays)") rather than specific reasoning instructions. A specialist told it is "an expert on CPF contributions" still relies entirely on its training data for the substance of that expertise.

**W14. No reasoning scaffolding in specialist prompts**. The QueryAnalyzer uses a basic chain-of-thought structure (Step 1 through Step 4), but specialist agents have no reasoning scaffolding. They are told "produce a structured advisory" without guidance on how to reason through a regulatory analysis. For complex scenarios (e.g., "Can I dismiss this employee?"), the specialist needs structured reasoning: identify the employee category, check Part IV applicability, assess misconduct severity, verify due inquiry requirements.

**W15. Prompts do not teach common regulatory mistakes**. The system prompts do not warn about frequent misapplications of Singapore employment law. For example: applying Part IV protections to managers/executives earning above $2,600, confusing CPF contribution rates for citizens vs. PRs vs. foreigners, misunderstanding that the Employment Act covers all employees (not just Part IV workers) for basic protections. These are exactly the mistakes an LLM would make without specific guidance.

**W16. Response synthesizer has no tone or structure guidance**. The synthesizer is told to "write for non-HR-professionals" and "structure with short paragraphs." It has no guidance on response length, heading structure, whether to use bullet points, how to handle partial answers (when one specialist was confident but another was not), or how to present conflicting specialist opinions.

**W17. No few-shot examples in any prompt**. None of the system prompts include worked examples of correct input-output pairs. For a classification task (QueryAnalyzer) and a structured output task (all agents), few-shot examples dramatically improve output quality and consistency.

#### Missing Capabilities

**W18. No clarification mechanism**. When a query is ambiguous ("My staff wants to leave" -- resign or take leave?), the system classifies and answers without asking. There is no mechanism for the advisory pipeline to request clarification from the user before proceeding.

**W19. No scenario detection for complex multi-step situations**. Some HR situations follow a standard procedural sequence (termination, MOM inspection, TADM claim). The emergency responses module handles these as static data, but the agent pipeline does not detect when a user's question maps to an emergency scenario and should trigger the structured response instead of a general advisory.

**W20. No "what-if" scenario modeling**. Users often want to understand the implications of a decision before making it ("If I hire two more foreign workers, will I exceed my quota?"). The quota/levy calculator supports this, but the agent pipeline does not detect scenario-modeling intent or route to the appropriate calculator.

**W21. No document generation integration in the pipeline**. The DocumentGenerationAgent exists but is not part of the orchestration flow. When a user asks "I need a termination letter," the query analyzer would classify this as an employment_act query and route to the EmploymentActAgent, which would provide advisory text rather than generating a document.

### 1.4 Component Quality Assessment

| Component                | Quality                             | Notes                                                           |
| ------------------------ | ----------------------------------- | --------------------------------------------------------------- |
| QueryAnalyzerAgent       | Good                                | Clean classification logic, proper validation, Singlish support |
| OrchestratorAgent        | Redundant                           | Can be replaced with deterministic dispatch                     |
| EmploymentActAgent       | Adequate                            | Prompt needs domain-specific reasoning depth                    |
| CPFAgent                 | Adequate                            | Needs rate-specific reasoning, PR handling guidance             |
| ForeignManpowerAgent     | Adequate                            | Needs COMPASS-specific prompt enrichment                        |
| FairEmploymentAgent      | Adequate                            | Needs WFL (2025) integration, TAFEP process detail              |
| TaxAgent                 | Adequate                            | Needs IR21 timeline specificity, BIK valuation rules            |
| WSHAgent                 | Adequate                            | Needs sector-specific safety requirements                       |
| ComplianceAgent          | Good                                | Well-designed but not wired into pipeline                       |
| ResponseSynthesizerAgent | Adequate                            | Needs tone, structure, and conflict resolution guidance         |
| CalculatorAgent          | Strong                              | Deterministic, well-structured, correct formulas                |
| DocumentGenerationAgent  | Adequate                            | Not integrated into pipeline                                    |
| SharedMemoryPool         | Good                                | Proper metadata validation, tag-based retrieval                 |
| ShortTermMemory          | Good                                | Turn-based with entity/domain merging                           |
| LongTermMemory           | Skeletal                            | In-memory only, no DataFlow backend yet                         |
| KB Pipeline              | Strong                              | Bulk loading, validation, cross-references                      |
| Citation Validator       | Good design, partial implementation | Hardcoded registry needs DB backend                             |
| Disclaimer System        | Strong                              | Three-tier with verification gradient                           |
| Guardrails               | Strong                              | Circumvention detection, escalation triggers, content filtering |
| Trust Layer (EATP)       | Strong design, not wired            | Complete data model, unused during queries                      |
| Learning Pipeline        | Strong design, not wired            | Feedback taxonomy, gap detection, monthly reports               |
| Emergency Responses      | Strong                              | Six comprehensive crisis scenarios                              |
| Sector Playbooks         | Strong                              | Six sectors with tailored compliance challenges                 |
| Growth Triggers          | Strong                              | Seven threshold-based proactive alerts                          |
| Singlish Support         | Good                                | 16 phrase mappings, system prompt additions                     |

---

## 2. Recommended Agent/Skills Structure

### 2.1 Architectural Changes

#### Change 1: Remove the OrchestratorAgent, replace with deterministic dispatch

The QueryAnalyzer already produces a structured routing decision. The Orchestrator adds an LLM round-trip to reprocess the same information. Replace it with a deterministic `DispatchRouter` function:

```python
class DispatchRouter:
    """Deterministic specialist dispatch based on QueryAnalyzer output."""

    def route(self, analysis: dict) -> DispatchPlan:
        domains = analysis["domains"]
        routing = analysis["routing_decision"]

        specialists = []
        for domain in domains[:3]:  # max 3 specialists
            if domain in DOMAIN_TO_SPECIALIST:
                specialists.append(domain)

        mode = routing.get("strategy", "parallel")
        if len(specialists) == 1:
            mode = "router"

        return DispatchPlan(mode=mode, specialists=specialists)
```

Savings: One LLM call per query (512 max_tokens). Latency reduction: 1-3 seconds. No loss of routing quality -- the fallback plan in the current Orchestrator already demonstrates this logic works deterministically.

#### Change 2: Wire KB retrieval into the specialist dispatch path

Before calling each specialist, the pipeline must:

1. Query the embedding index for provisions relevant to the user's query within the specialist's domain
2. Pass the retrieved provisions as `relevant_provisions` to the specialist

```python
# In the pipeline execution flow:
provisions = kb_retriever.search(
    query=query_text,
    domain=specialist_domain,
    top_k=10,
)
specialist.advise(
    query_text=query_text,
    company_context=company_context,
    relevant_provisions=provisions,
)
```

This is the single most important change. Without grounded provisions, specialists are advising from LLM training data, which defeats the purpose of the knowledge base.

#### Change 3: Add a QueryClarifier stage before classification

Insert a lightweight pre-classification check for ambiguity:

```python
class QueryClarifierAgent(BaseAgent):
    """Detect ambiguity and request clarification when needed."""

    def clarify(self, query: str, conversation_history: str) -> ClarificationResult:
        # Returns either:
        # - proceed=True (query is clear enough)
        # - proceed=False with clarification_question (ask user first)
        pass
```

This agent uses very low max_tokens (256) and low temperature (0.0). It only fires when the query is genuinely ambiguous, not on every turn.

#### Change 4: Wire the ComplianceAgent as a mandatory post-specialist gate

The ComplianceAgent should always run after specialists (for queries involving 2+ domains). Its output should be available to the ResponseSynthesizer to flag contradictions.

#### Change 5: Wire trust lineage recording into the pipeline

Every query should create a genesis record, every agent call should create an attestation, and constraint envelope validation should run before specialist outputs are accepted. This is already designed -- it just needs to be called.

#### Change 6: Add intent detection for action routing

The QueryAnalyzer should detect action intents (calculate, generate document, check compliance, emergency) and route to the appropriate handler:

```
"How do I calculate CPF for my worker?" -> CalculatorAgent (deterministic)
"I need a termination letter" -> DocumentGenerationAgent
"My worker got injured just now" -> EmergencyResponse (structured data)
"Check my compliance status" -> ComplianceChecker (deterministic)
"What are my leave obligations?" -> Specialist pipeline (advisory)
```

### 2.2 Recommended Agent Structure

```
Tier 0: Pre-processing (no LLM)
  - GuardrailScreener        (regex-based query screening)
  - SinglishNormalizer        (phrase mapping, no LLM needed)
  - EmergencyDetector         (pattern match to emergency scenarios)

Tier 1: Classification (1 LLM call)
  - QueryAnalyzerAgent        (enhanced with intent detection + clarification)

Tier 2: Deterministic Routing (no LLM)
  - DispatchRouter            (replaces OrchestratorAgent)
  - KBRetriever               (vector search for relevant provisions)

Tier 3: Domain Advisory (1-3 LLM calls, parallel)
  - EmploymentActAgent        (enhanced prompt with reasoning scaffolding)
  - CPFAgent                  (enhanced with rate table awareness)
  - ForeignManpowerAgent      (enhanced with COMPASS framework detail)
  - FairEmploymentAgent       (enhanced with WFL 2025 provisions)
  - TaxAgent                  (enhanced with IR21/BIK specifics)
  - WSHAgent                  (enhanced with sector-specific requirements)
  - PDPAAgent                 (NEW: data protection specialist)

Tier 3-alt: Action Handlers (deterministic or 1 LLM call)
  - CalculatorAgent           (existing, deterministic)
  - DocumentGenerationAgent   (existing, 1 LLM call)
  - ComplianceCheckerAgent    (existing, deterministic)
  - EmergencyResponseHandler  (existing, structured data)

Tier 4: Quality Gate (1 LLM call, only for multi-domain queries)
  - ComplianceAgent           (cross-domain consistency check)

Tier 5: Synthesis (1 LLM call)
  - ResponseSynthesizerAgent  (enhanced with tone/structure guidance)

Tier 6: Post-processing (no LLM)
  - CitationValidator         (DB-backed provision validation)
  - DisclaimerApplier         (risk-tier disclaimers)
  - TrustRecorder             (EATP attestation, genesis record)
  - FeedbackRecorder          (learning pipeline input)
```

**Typical query cost**: 3 LLM calls (Analyzer + 1 Specialist + Synthesizer)
**Complex query cost**: 5 LLM calls (Analyzer + 2 Specialists + Compliance + Synthesizer)
**Current cost**: 4+ LLM calls (Analyzer + Orchestrator + Specialists + Synthesizer)

### 2.3 New Agent: PDPAAgent

Data protection is a growing regulatory domain in Singapore. The system already has PDPA provisions, emergency response data, and sector playbook references. A dedicated specialist closes a real coverage gap.

```python
class PDPAAgent(BaseDomainSpecialist):
    domain = "pdpa"
    domain_label = "Data Protection"

    # Covers:
    # - PDPA obligations (consent, purpose limitation, access, correction)
    # - Mandatory breach notification (3-day PDPC notification)
    # - Data Protection Officer (DPO) appointment requirements
    # - Cross-border data transfer rules
    # - Employee data handling (NRIC, medical records, performance data)
    # - PDPC enforcement and penalties
```

### 2.4 Memory Architecture Recommendations

**Short-term memory** should be wired so that:

1. Every turn saves query, response, entities, domains, and risk tier
2. The QueryAnalyzer receives formatted conversation history
3. The ResponseSynthesizer receives recent entity context for pronoun resolution

**Long-term memory** should be wired so that:

1. Company profile is loaded at session start and enriched with stored context
2. Frequently asked topics inform the QueryAnalyzer's prior expectations
3. Previous advisory records allow the system to say "As we discussed previously..."

**Shared memory pool** should be enhanced with:

1. Provision retrieval results (so the synthesizer can verify citation sources)
2. Calculator outputs (when a calculation was performed)
3. Emergency response references (when a crisis scenario was detected)

---

## 3. System Prompt Optimization Guide

### 3.1 QueryAnalyzerAgent

**Current issues**: Basic four-step classification with no examples. No intent detection beyond domain classification. No handling of action-oriented queries.

**Recommended prompt**:

```
You are a Singapore HR regulatory query classifier for Arbor, an advisory platform serving SME employers.

TASK: Classify the user's HR query. Do NOT answer it. Only classify and route.

== INTENT DETECTION ==

First, determine the user's primary intent:
- ADVISORY: Asking for guidance on a regulatory topic ("What are my leave obligations?")
- CALCULATION: Asking for a numerical answer ("How much CPF for a $5,000 salary?")
- DOCUMENT: Requesting a document or template ("I need a termination letter")
- EMERGENCY: Reporting a crisis situation ("Employee injured at work", "Received TADM claim")
- COMPLIANCE_CHECK: Asking about their overall compliance ("Am I doing everything right?")
- CLARIFICATION_NEEDED: Query is too ambiguous to classify reliably

== DOMAIN CLASSIFICATION ==

Assign one or more domains. Choose from:
  employment_act:    EA matters (leave, termination, hours, salary, notice, Part IV, KETs, payslips)
  cpf:              CPF contributions, rates, ceilings, PR graduated rates, e-submission
  foreign_manpower: Work passes (EP, S Pass, WP), COMPASS, DRC quotas, levies, EFMA conditions
  fair_employment:  TAFEP, WFL, FWA, anti-discrimination, grievance handling, fair recruitment
  tax:              IRAS employer obligations, IR21, BIK, withholding tax, AIS, Appendix 8A/8B
  wsh:              WSH Act, risk assessments, incident reporting, iReport, WSH officer duties
  pdpa:             Personal Data Protection Act, breach notification, DPO, consent
  compliance:       Cross-domain compliance questions spanning multiple acts
  general:          General HR questions not specific to any act

== ENTITY EXTRACTION ==

Extract all identifiable entities:
  company_name, employee_type (workman/non-workman/manager/executive), salary_amount,
  dates, headcount, sector, nationality, pass_type, years_of_service, leave_type,
  calculation_type

== RISK TIER ==

  green:  Straightforward, well-documented topic with clear statutory answer
  amber:  Involves thresholds, edge cases, multiple acts, or depends on specific facts
  red:    Potential litigation, penalty exposure, contradictory requirements, or misconduct

When in doubt, assign the HIGHER risk tier.

== ROUTING DECISION ==

  router:     Single specialist needed
  parallel:   Multiple independent specialists needed
  sequential: One specialist's output feeds another (e.g., EA determines coverage, then CPF applies)

== EXAMPLE ==

Query: "My part-time worker earning $1,800 asked about overtime. Also need to know CPF."
Output:
{
  "intent": "advisory",
  "domains": ["employment_act", "cpf"],
  "entities": {"employee_type": "part-time", "salary_amount": 1800},
  "risk_tier": "green",
  "routing_decision": {"strategy": "parallel", "specialists": ["employment_act", "cpf"]}
}

Query: "How much CPF I need pay for my staff salary $6,000?"
Output:
{
  "intent": "calculation",
  "domains": ["cpf"],
  "entities": {"salary_amount": 6000},
  "risk_tier": "green",
  "routing_decision": {"strategy": "router", "specialists": ["cpf"]}
}

If conversation_history is provided, use it to resolve pronouns and references.

OUTPUT: Respond ONLY with a valid JSON object.
```

### 3.2 Specialist Agent Prompts (General Template)

**Current issues**: All specialists use identical prompt templates with only the domain name changed. No reasoning scaffolding. No common-mistake warnings. No few-shot examples.

**Recommended enhanced template** (each specialist customizes the [DOMAIN-SPECIFIC] sections):

```
You are a Singapore [DOMAIN] specialist providing advisory guidance through Arbor.

== YOUR CONSTRAINT ENVELOPE ==
You may ONLY advise on matters covered by [ACTS/REGULATIONS].
If the query falls outside your domain, respond with:
  "answer_text": "This query is about [identified domain], which is outside my scope."
  "cross_domain_flags": ["identified_domain"]

== HOW TO REASON ==

Follow this analytical structure for every query:

STEP 1 - IDENTIFY APPLICABILITY
  - Who is the employee? (workman, non-workman, manager, executive, foreign worker)
  - What are the salary thresholds? (Part IV: workman any salary, non-workman <= $2,600)
  - Does [ACT] apply to this situation?

STEP 2 - FIND RELEVANT PROVISIONS
  - Search the relevant_provisions input for applicable sections
  - If no relevant provision is found, state this explicitly
  - Do NOT cite provisions from memory -- ONLY from the relevant_provisions input

STEP 3 - APPLY TO THE FACTS
  - Apply the provision to the specific facts in the query
  - Consider the company context (sector, headcount, foreign workers)
  - Note any thresholds, deadlines, or conditions

STEP 4 - ASSESS RISK
  - green: Clear statutory answer, low ambiguity
  - amber: Depends on specific facts, involves thresholds or edge cases
  - red: Potential penalty, litigation risk, or requires due process

STEP 5 - FLAG CROSS-DOMAIN IMPLICATIONS
  - Does this situation also involve other regulatory domains?
  - Example: Termination always involves EA (notice), CPF (final contribution), Tax (IR21)

== COMMON MISTAKES TO AVOID ==
[DOMAIN-SPECIFIC MISTAKES - see per-specialist sections below]

== CITATION FORMAT ==
  Use: ([ACT ABBREVIATION] s.XX) in the answer text
  In cited_provisions: [{"provision_id": ID, "section": "...", "act": "..."}]
  NEVER fabricate a section number. If unsure, say "refer to [general area of the Act]."

== CONFIDENCE CALIBRATION ==
  0.9-1.0: Direct statutory answer with clear provision
  0.7-0.8: Correct interpretation but involves some judgment
  0.5-0.6: Partial answer, missing facts, or edge case
  Below 0.5: Insufficient information or provisions to advise reliably

OUTPUT: Respond ONLY with a valid JSON object.
```

### 3.3 Per-Specialist Customizations

#### EmploymentActAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- Part IV does NOT cover all employees. It covers workmen (any salary) and non-workmen
  earning <= $2,600/month. Managers and executives earning above $2,600 are NOT covered
  by Part IV hours/overtime/rest day provisions.
- Part IV protections are DIFFERENT from general EA coverage. ALL employees are covered
  by the EA for basic protections (salary payment, KETs, payslips, leave). Only Part IV
  adds hours/overtime/rest day protections.
- Notice period defaults (if not stated in contract): 1 day (< 26 weeks), 1 week
  (26 weeks to < 2 years), 2 weeks (2 to < 5 years), 4 weeks (5+ years).
- Dismissal for misconduct (s14) requires a due inquiry. Summary dismissal without
  inquiry is wrongful even if the misconduct is genuine.
- Salary deductions are limited by s27. Cannot deduct more than 50% of total salary in
  any one salary period.
- Retrenchment benefit is NOT statutory. It is market practice (typically 2 weeks to
  1 month per year of service). Never state that retrenchment benefit is required by law.
```

#### CPFAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- CPF rates differ by citizenship status: Singapore Citizen, Singapore PR, and Foreigner.
  Foreigners do NOT contribute to CPF. PRs have graduated rates in years 1 and 2.
- The OW ceiling is $8,000/month (2026). Wages above this cap do NOT attract CPF on
  the excess. The AW ceiling is $102,000/year minus total OW subject to CPF.
- PR graduated rates: Year 1 and Year 2 PRs may opt for full employer+employee rates
  or graduated rates. This is a joint employer-employee election.
- CPF is payable on TOTAL remuneration including allowances, commissions, and bonuses
  (as additional wages), not just basic salary.
- Late payment interest is 18% per annum (CPF Act s52). There is no grace period.
- Stock option gains and certain one-off payments have specific CPF treatment rules.
  Do not assume all payments are subject to CPF.
```

#### ForeignManpowerAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- DRC quotas differ by sector: Services (35% S Pass, 8% WP), Manufacturing, Construction.
  Do not apply one sector's ratio to another.
- COMPASS is a points-based system for EP applications. It is NOT a quota system. An EP
  application can score well on COMPASS and still be refused on other grounds.
- EP holders are NOT covered by Part IV of the Employment Act (no overtime, rest day,
  or hours of work protections). They ARE covered by basic EA protections.
- S Pass and WP holders ARE covered by Part IV (as they earn below the threshold).
- Foreign worker levy is the employer's obligation and CANNOT be deducted from the worker's salary.
- Employers must NOT retain a foreign worker's passport, work permit, or personal belongings.
```

#### FairEmploymentAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- The Workplace Fairness Act (effective 2025) makes discrimination in employment decisions
  an offence with legal remedies. This is a legislative change from the earlier guideline-only approach.
- TAFEP guidelines are tripartite GUIDELINES, not legislation (except for advertising on
  MyCareersFuture). However, non-compliance can trigger MOM scrutiny and affect EP applications.
- The Fair Consideration Framework (FCF) requires advertising on MyCareersFuture for 14
  calendar days. Exemptions exist for companies with fewer than 10 employees and for
  short-term roles (< 1 month) and intra-corporate transfers.
- FWA requests (TG-FWAR, effective Dec 2024): Employers must respond within 2 months and
  cannot unreasonably refuse. But "unreasonable" is assessed case by case.
- Protected characteristics under the WFL include age, race, religion, gender, marital status,
  disability, and mental health condition. Sexual orientation is NOT currently a protected
  characteristic under the WFL.
```

#### TaxAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- IR21 (tax clearance) must be filed at least 1 month BEFORE the employee's last working
  day for Singaporeans/PRs ceasing employment, and at least 2 months before for
  non-citizens/non-PRs. Do not confuse the timelines.
- Benefits-in-kind (BIK) are taxable to the employee. Common BIK items include
  accommodation, car benefit, driver, and club membership. Formula-based valuation
  rules apply (Appendix 8A).
- Stock options granted under an ESOP are taxable as employment income at exercise, not
  at grant. The taxable gain is the difference between the exercise price and the market
  value on the date of exercise.
- Withholding tax obligations apply to payments to non-resident employees (directors' fees,
  consultancy fees). Rate is typically 15% for employment income and 22% for directors' fees.
- AIS (Auto-Inclusion Scheme) is mandatory for employers with 5+ employees. Employment
  income is reported directly to IRAS electronically by 1 March each year.
```

#### WSHAgent -- Common Mistakes Section

```
== COMMON MISTAKES TO AVOID ==
- WSH Act duties apply to ALL workplaces, not just construction or manufacturing sites.
  An office is also a workplace under the WSH Act.
- Incident reporting to MOM (iReport) is required within 10 days for injuries resulting
  in more than 3 consecutive days of medical leave. Fatal or dangerous occurrences must
  be reported within 24 hours.
- WSH Officer appointment is mandatory for certain sectors when the workplace has 50+
  workers. This is not a general obligation for all companies.
- Risk assessments must be conducted for all work activities. These must be documented
  and reviewed when there are changes to work processes.
- WICA insurance is mandatory for ALL employees (not just manual workers). Employers
  must maintain WICA insurance coverage.
```

### 3.4 ResponseSynthesizerAgent

**Current issues**: No tone guidance, no structure template, no conflict resolution instructions, no length guidance.

**Recommended enhanced prompt**:

```
You are the final advisory response writer for Arbor, a Singapore HR advisory platform
serving SME employers and managers. You transform specialist agent outputs into a clear,
actionable, authoritative response.

== YOUR AUDIENCE ==
SME owners and managers who are NOT HR professionals. They want to know:
  1. What they need to do (specific actions)
  2. Why (which law/regulation requires it)
  3. When (deadlines, timelines)
  4. What happens if they don't (penalties, risks)

== RESPONSE STRUCTURE ==

Use this structure consistently:

**Summary** (1-2 sentences answering the core question)

**What the law says** (cite specific provisions in parentheses)

**What you need to do** (numbered action steps with deadlines)

**Watch out for** (risks, common pitfalls, cross-domain implications)

**Disclaimer** (if amber or red risk tier)

== TONE RULES ==
- Warm, professional, direct. Not bureaucratic or legalistic.
- Use "you" and "your" (addressing the employer directly).
- Use active voice: "You must issue payslips" not "Payslips must be issued."
- Do not hedge with phrases like "it may be advisable" or "you might want to consider."
  Be direct: "You must" (for statutory obligations) or "You should" (for best practices).

== CITATION RULES ==
- Cite provisions in parentheses within the text: (Employment Act s.13(1))
- Only cite provisions that appear in the specialist outputs. NEVER fabricate citations.
- If a specialist cited a provision, include it. If no provision supports a claim, do not
  make the claim.

== CONFLICT RESOLUTION ==
If two specialists provide conflicting information:
  1. Note both positions
  2. Explain the source of the conflict (e.g., "The Employment Act provides X, while
     the CPF Act requires Y -- both apply.")
  3. Elevate the risk tier to amber (if it was green) or red (if it was amber)
  4. Recommend professional review for the conflicting aspect

== PARTIAL CONFIDENCE ==
If a specialist expressed low confidence (< 0.6) on part of the answer:
  1. Present the confident parts as advisory
  2. Flag the low-confidence parts: "For [specific aspect], we recommend confirming with
     a professional as the answer depends on your specific circumstances."

== LENGTH GUIDANCE ==
- Green tier: 150-300 words (straightforward questions get concise answers)
- Amber tier: 250-500 words (nuanced situations need more explanation)
- Red tier: 300-600 words (high-risk situations need thorough treatment)
- Never pad with generic advice. Every sentence should add specific value.

== RISK TIER DISCLAIMERS ==
- Green: No disclaimer needed. Citations serve as the transparency mechanism.
- Amber: Append: "This topic involves nuances that may vary by your specific circumstances.
  We recommend reviewing with an HR professional before acting."
- Red: Append: "This situation carries significant legal or financial risk. We strongly
  recommend consulting an employment law specialist before taking any action."

You may ESCALATE the risk tier from the input value but NEVER downgrade it.

OUTPUT: Respond ONLY with a valid JSON object.
```

---

## 4. Quality Rubric

### 4.1 Scoring Framework

Each dimension is scored 1-5. An acceptable advisory response scores at least 3 on every dimension and at least 4 on Legal Accuracy and Risk Awareness. Responses scoring 1 or 2 on any dimension should be flagged for review.

### 4.2 Dimension 1: Legal Accuracy

| Score                         | Description                                                                                                                                                                                                               |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Authoritative**        | Correct law cited with correct section number. Interpretation matches the statutory text and established precedent. Thresholds, amounts, and deadlines are current and precise. No errors of omission on material points. |
| **4 -- Accurate**             | Correct law and section cited. Interpretation is sound. Minor omissions that do not affect the practical advice (e.g., mentioning the general rule but not a rare exception).                                             |
| **3 -- Mostly Accurate**      | Correct law identified but section number is approximate or missing. Interpretation captures the main point but may miss an important condition or qualifier.                                                             |
| **2 -- Partially Inaccurate** | The general direction is correct but contains a material error: wrong threshold, wrong employee category, outdated rate, or misapplied provision. Following this advice could lead to a compliance gap.                   |
| **1 -- Incorrect**            | Wrong law cited, or correct law but fundamentally wrong interpretation. Following this advice would create legal exposure.                                                                                                |

**Red flags (automatic score 1)**:

- Stating that retrenchment benefit is statutory
- Applying Part IV to managers/executives above the salary threshold
- Quoting wrong CPF rates for the employee's citizenship/age category
- Fabricating a provision section number
- Confusing EFMA rules between pass types

### 4.3 Dimension 2: Contextual Relevance

| Score                             | Description                                                                                                                                                                                                                                                                             |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Fully Contextualized**     | Response uses the company profile (sector, headcount, foreign workers) and conversation history to tailor advice. Sector-specific rules are applied where they differ from the general case. The answer addresses the user's specific situation, not a generic version of the question. |
| **4 -- Well Contextualized**      | Response references available context and adapts advice accordingly. May miss one sector-specific nuance but the core advice is tailored.                                                                                                                                               |
| **3 -- Partially Contextualized** | Response acknowledges the context but does not fully apply it. Gives correct general advice that may not perfectly fit the specific situation.                                                                                                                                          |
| **2 -- Generic**                  | Response provides textbook-correct information but ignores the user's specific context. Does not reference company size, sector, or other provided details.                                                                                                                             |
| **1 -- Irrelevant**               | Response addresses a different situation than what was asked, or provides advice for the wrong employee category, sector, or regulatory domain.                                                                                                                                         |

### 4.4 Dimension 3: Conversational Coherence

| Score                  | Description                                                                                                                                                                                                           |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Seamless**      | Response correctly resolves all pronouns and references from prior turns. Builds on previous answers without repeating information already given. Acknowledges when the current question relates to an earlier topic. |
| **4 -- Coherent**      | Response resolves most references from prior turns. Minor repetition but generally builds on the conversation.                                                                                                        |
| **3 -- Adequate**      | Response is standalone-correct but does not deeply connect to prior conversation. Does not contradict earlier answers.                                                                                                |
| **2 -- Disconnected**  | Response ignores relevant prior context. Contradicts or repeats earlier advice without acknowledgment.                                                                                                                |
| **1 -- Contradictory** | Response directly contradicts an earlier advisory in the same session, or misresolves a pronoun from prior turns leading to advice about the wrong entity.                                                            |

### 4.5 Dimension 4: Actionability

| Score                           | Description                                                                                                                                                                                                                                                                              |
| ------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Immediately Actionable** | Response provides numbered steps with specific deadlines, identifies responsible parties, names the forms or systems to use (e.g., "File via iReport on the MOM website"), and specifies the consequence of inaction. The user can act on this advice today without additional research. |
| **4 -- Actionable**             | Response provides clear steps and deadlines. May lack one specific detail (e.g., the exact form name) but the user knows what to do and when.                                                                                                                                            |
| **3 -- Directional**            | Response explains what needs to happen but lacks specific steps or timelines. The user understands the obligation but would need to research the "how."                                                                                                                                  |
| **2 -- Vague**                  | Response identifies the topic area but gives only general guidance like "you should comply with the relevant regulations" or "consult MOM's website."                                                                                                                                    |
| **1 -- Not Actionable**         | Response is purely informational with no guidance on what the user should do. Or provides so many options and qualifications that the user is more confused than before.                                                                                                                 |

### 4.6 Dimension 5: Risk Awareness

| Score                             | Description                                                                                                                                                                                                                                                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Precise Risk Calibration** | Risk tier is correctly assigned. High-stakes situations (termination, discrimination, injury) are flagged as amber or red. Specific penalties and consequences are mentioned. Professional review recommendation is appropriately timed -- present for amber/red, absent for green. Escalation triggers are correctly identified. |
| **4 -- Good Risk Awareness**      | Risk tier is correct. Major risks are identified. Professional review recommendation is present when needed. May not mention specific penalty amounts.                                                                                                                                                                            |
| **3 -- Adequate Risk Awareness**  | Risk tier is approximately correct (may understate by one level). General risk awareness is present but not specifically calibrated to the scenario.                                                                                                                                                                              |
| **2 -- Underestimates Risk**      | Classifies a genuinely risky situation as green, or omits a professional review recommendation when one is warranted. Could lead the user to act without appropriate caution.                                                                                                                                                     |
| **1 -- Risk Blind**               | No risk assessment. Treats a high-stakes situation (e.g., dismissal during pregnancy, workplace fatality) as routine. No escalation recommendation.                                                                                                                                                                               |

**Red flags (automatic score 1)**:

- Classifying wrongful dismissal allegations as green
- Not recommending professional review for active litigation
- Not mentioning MOM reporting obligations for workplace injuries

### 4.7 Dimension 6: Citation Quality

| Score                          | Description                                                                                                                                                                                                          |
| ------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Precise and Relevant**  | Every cited provision directly supports the specific claim it accompanies. Section numbers are correct. No irrelevant citations (padding). Authority level is appropriate (statute vs. guideline vs. best practice). |
| **4 -- Good Citations**        | Citations are relevant and correct. May include one citation that is broadly relevant rather than precisely targeted.                                                                                                |
| **3 -- Adequate Citations**    | Citations are present and generally relevant but may lack section-level specificity (citing "Employment Act" instead of "EA s.13(1)").                                                                               |
| **2 -- Weak Citations**        | Citations are present but some are irrelevant or incorrect. Citation padding (including provisions that are tangentially related to appear thorough).                                                                |
| **1 -- Missing or Fabricated** | No citations provided, or citations reference non-existent provisions, or citations are fabricated (section numbers that do not exist in the cited Act).                                                             |

### 4.8 Dimension 7: Language Understanding

| Score                          | Description                                                                                                                                                                                                                             |
| ------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Native Understanding**  | Correctly interprets Singlish, code-switching, and colloquial phrasing. Does not ask the user to rephrase. Responds in clear standard English while being warm and accessible. Handles abbreviated HR terms (OT, MC, AL, PH) naturally. |
| **4 -- Good Understanding**    | Correctly interprets most Singlish and colloquial input. May miss a nuanced colloquial term but gets the intent right. Response tone is appropriate.                                                                                    |
| **3 -- Adequate**              | Understands the core question but may miss Singlish-specific meaning (e.g., interpreting "never take" literally as "never" rather than "did not use"). Responds appropriately.                                                          |
| **2 -- Partial Understanding** | Misinterprets some Singlish or colloquial phrasing, leading to a response that addresses a slightly different question. Or asks the user to rephrase.                                                                                   |
| **1 -- Fails to Understand**   | Cannot parse Singlish input. Asks user to "please rephrase in English." Or provides a completely off-topic response due to language misunderstanding.                                                                                   |

### 4.9 Dimension 8: Completeness

| Score                  | Description                                                                                                                                                                                                                                                                                                                                                                 |
| ---------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **5 -- Comprehensive** | Addresses every aspect of the question. Covers the primary obligation and all related obligations the user should know about (e.g., for a termination question: notice period AND final payment AND CPF final contribution AND IR21 AND accrued leave AND KET/payslip records). Proactively mentions "you should also know..." for commonly overlooked related obligations. |
| **4 -- Complete**      | Addresses the primary question fully and mentions the most important related obligations. Does not leave out anything that would cause immediate compliance issues.                                                                                                                                                                                                         |
| **3 -- Adequate**      | Addresses the primary question but omits one or two related obligations. The user gets the core answer but may not realize there are additional steps.                                                                                                                                                                                                                      |
| **2 -- Incomplete**    | Addresses part of the question and omits significant related obligations. The user might comply on one front but inadvertently violate another.                                                                                                                                                                                                                             |
| **1 -- Fragmentary**   | Only addresses one small aspect of a multi-part question, or provides an answer so brief that it is not useful for decision-making.                                                                                                                                                                                                                                         |

### 4.10 Overall Quality Score

The overall quality score is the minimum of all eight dimension scores (not the average). The system is only as strong as its weakest dimension.

| Overall | Grade           | Meaning                                                               |
| ------- | --------------- | --------------------------------------------------------------------- |
| 5       | Exceptional     | Advisory quality matches or exceeds a competent HR consultant         |
| 4       | Good            | Reliable for routine queries; appropriate escalation for complex ones |
| 3       | Acceptable      | Adequate for informational queries; needs improvement for advisory    |
| 2       | Below Threshold | Material quality gaps; should not be served without human review      |
| 1       | Unacceptable    | Contains errors that could cause legal or financial harm              |

### 4.11 Automated Quality Checks

The following checks can be automated without human judgment:

| Check                  | Method                                        | Pass Condition                           |
| ---------------------- | --------------------------------------------- | ---------------------------------------- |
| Citation existence     | Cross-reference cited provisions against KB   | All cited provisions exist in KB         |
| Citation currency      | Check provision effective dates               | No expired provisions cited              |
| Risk tier consistency  | Compare specialist risk tiers with final tier | Final tier >= max(specialist tiers)      |
| Domain scope           | Validate specialist answered within domain    | No constraint envelope violations        |
| Response structure     | Check for required sections                   | Summary, provisions, actions present     |
| Disclaimer presence    | Check for risk-tier disclaimer                | Amber/red responses include disclaimer   |
| Confidence threshold   | Check specialist confidence scores            | No response served with confidence < 0.3 |
| Length appropriateness | Measure response token count                  | Within tier-appropriate range            |

---

## 5. Self-Improvement Architecture

### 5.1 Feedback Collection Points

The learning pipeline (already designed in `learning_pipeline.py`) needs to be wired to collect feedback at three levels:

**Level 1: Explicit user feedback**

- Thumbs up/down on each response
- Optional category selection for thumbs-down (wrong answer, outdated info, unclear, missing topic, irrelevant, too generic)
- Free-text correction field ("What should the answer have been?")

**Level 2: Implicit behavioral signals**

- User asks the same question rephrased (indicates unsatisfactory first answer)
- User asks a follow-up in a different domain (may indicate cross-domain gap)
- Session ends immediately after a response (may indicate the response was sufficient -- or the user gave up)
- User asks to speak to a human (clear dissatisfaction signal)

**Level 3: Expert audit feedback**

- Monthly random sampling of responses for human expert review
- Scoring against the quality rubric (Section 4)
- Specific corrections recorded with corrected provision/interpretation

### 5.2 Feedback-to-Action Pipeline

```
Feedback
    |
    v
Categorize (automatic + human review for ambiguous cases)
    |
    +--> Wrong Answer       --> KB correction or prompt refinement
    +--> Outdated Info      --> KB update + rate table update
    +--> Unclear            --> Prompt refinement (response synthesizer)
    +--> Missing Topic      --> KB gap detection --> KB expansion priority
    +--> Irrelevant         --> Routing improvement (query analyzer)
    +--> Too Generic        --> Prompt refinement (specialist or synthesizer)
```

### 5.3 Prompt Improvement Loop

System prompts should be version-controlled and updatable through the learning pipeline. The improvement cycle:

1. **Detect pattern**: Multiple thumbs-down on similar queries in the same domain
2. **Diagnose root cause**: Expert reviews the failing responses against the rubric
3. **Draft improvement**: Propose a prompt change (new common-mistake, reasoning step, or few-shot example)
4. **Test against regression suite**: Run the updated prompt against the 40+ baseline test scenarios
5. **Human review gate**: CARE governance requires human approval for prompt changes (same as KB content changes)
6. **Deploy with A/B monitoring**: New prompt version runs alongside old version for 1 week
7. **Confirm improvement**: Compare quality scores between versions before full deployment

### 5.4 KB Gap Detection

The system should track which queries receive low-confidence responses and correlate them with domains:

```python
# Triggered when specialist confidence < 0.6
def record_low_confidence_query(
    query_text: str,
    domain: str,
    confidence: float,
    provisions_retrieved: list,
    provisions_used: list,
):
    # If provisions_retrieved is empty -> KB coverage gap
    # If provisions_retrieved but provisions_used is empty -> retrieval relevance gap
    # If provisions_used but confidence still low -> provision detail gap
    pass
```

When a domain accumulates 5+ low-confidence queries on a similar topic within 30 days, the system should generate a `KbGap` record with:

- The topic area
- Example queries
- Average confidence
- Suggested provisions to add or enhance
- Priority (based on query frequency and negative feedback count)

These gap records feed into the monthly report for expert review.

### 5.5 Routing Optimization

Track domain co-occurrence patterns to optimize the QueryAnalyzer's classification:

```python
# Example insight:
# "employment_act + cpf" co-occurs in 45% of termination-related queries
# Action: When query mentions termination, pre-route to both EA and CPF
```

When a domain pair co-occurs in more than 30% of queries for a specific topic, the QueryAnalyzer prompt should be updated with a new routing example showing this pattern.

### 5.6 Accuracy Regression Testing

The existing `accuracy_testing.py` provides 14 baseline scenarios. This should be expanded to 200+ scenarios covering:

- **40 per specialist domain** (7 domains x ~6 scenarios each = 42)
- **20 cross-domain scenarios** (queries spanning 2+ domains)
- **20 Singlish scenarios** (queries in colloquial Singapore English)
- **20 edge cases** (threshold boundary queries: salary exactly at Part IV cutoff, PR in year 2 of graduated rates)
- **20 negative scenarios** (queries that should be refused or escalated)
- **20 action-intent scenarios** (calculation, document generation, compliance check, emergency)
- **20 conversation continuation scenarios** (multi-turn with pronoun resolution)
- **20 sector-specific scenarios** (per-sector playbook validation)

Each scenario should include:

- Expected domains and provisions
- Expected risk tier
- Key facts that MUST appear in the response
- Anti-facts that must NOT appear (hallucination detection)
- Expected action steps (for actionability scoring)

The regression suite should run:

- **On every prompt change**: Full suite (blocks deployment if accuracy drops)
- **Weekly**: Random 20% sample (monitors for drift)
- **Monthly**: Full suite + new scenarios from user feedback (comprehensive audit)

### 5.7 Monthly Learning Report

The existing `MonthlyReport` structure should be generated and reviewed monthly:

```
=== Arbor Monthly Learning Report (March 2026) ===

USAGE
- Total queries: 4,230
- Unique sessions: 1,850
- Average turns per session: 2.3
- Top domains: employment_act (38%), cpf (22%), foreign_manpower (15%)

QUALITY
- Average quality score: 4.1 / 5.0
- Positive feedback rate: 87%
- Regression test pass rate: 96% (192/200)
- Failed scenarios: B03 (foreign_manpower, DRC calc wrong), C01 (cross-domain, missed WSH trigger)

KB GAPS DETECTED
1. [HIGH] Dormitory accommodation standards -- 12 queries, avg confidence 0.42
2. [MEDIUM] Stock option CPF treatment -- 8 queries, avg confidence 0.55
3. [MEDIUM] Progressive Wage Model retail cleaning -- 6 queries, avg confidence 0.48

ROUTING INSIGHTS
- employment_act + cpf co-occurrence: 42% (up from 38%)
- Suggested: Pre-route termination queries to both EA and CPF

PROMPT CHANGES PROPOSED
1. CPFAgent: Add PR graduated rate reasoning to common mistakes
2. ResponseSynthesizer: Add conflict resolution example for EA+CPF
3. QueryAnalyzer: Add "dormitory" as a trigger term for foreign_manpower

RECOMMENDATIONS FOR EXPERT REVIEW
- 3 KB expansion proposals
- 1 prompt refinement proposal
- 2 new regression test scenarios
```

### 5.8 Institutional Memory Accumulation

Over time, the system should build three compounding assets:

1. **Resolution patterns**: Successful advisory sequences for complex queries (e.g., "For termination during probation, the winning pattern is: EA specialist (s10, s14) + CPF specialist (final contribution) + Tax specialist (IR21) + Compliance check"). These patterns reduce future multi-agent coordination cost.

2. **Company profiles**: Persistent company context that enriches every future query ("This company is in construction with 35 employees and 12 foreign workers. They have asked about DRC quotas three times -- they are likely near their limit.").

3. **Clarification templates**: When a query type repeatedly requires clarification, generate a pre-built clarification question ("When you say 'my worker wants to leave,' do you mean they want to resign, or they are asking about their leave entitlement?").

These assets are stored via the existing LongTermMemory infrastructure (currently in-memory, designed for DataFlow backend persistence).

---

## Appendix A: File Reference

| Component                | File Path                                                      |
| ------------------------ | -------------------------------------------------------------- |
| Pipeline factory         | `src/hr_advisory/agents/__init__.py`                           |
| Agent configs            | `src/hr_advisory/agents/config.py`                             |
| Orchestration signatures | `src/hr_advisory/agents/signatures.py`                         |
| QueryAnalyzerAgent       | `src/hr_advisory/agents/orchestration/query_analyzer.py`       |
| OrchestratorAgent        | `src/hr_advisory/agents/orchestration/orchestrator.py`         |
| ResponseSynthesizerAgent | `src/hr_advisory/agents/orchestration/response_synthesizer.py` |
| BaseDomainSpecialist     | `src/hr_advisory/agents/specialists/_base.py`                  |
| Specialist signatures    | `src/hr_advisory/agents/specialists/signatures.py`             |
| EmploymentActAgent       | `src/hr_advisory/agents/specialists/employment_act.py`         |
| CPFAgent                 | `src/hr_advisory/agents/specialists/cpf.py`                    |
| ForeignManpowerAgent     | `src/hr_advisory/agents/specialists/foreign_manpower.py`       |
| FairEmploymentAgent      | `src/hr_advisory/agents/specialists/fair_employment.py`        |
| TaxAgent                 | `src/hr_advisory/agents/specialists/tax.py`                    |
| WSHAgent                 | `src/hr_advisory/agents/specialists/wsh.py`                    |
| ComplianceAgent          | `src/hr_advisory/agents/specialists/compliance.py`             |
| CalculatorAgent          | `src/hr_advisory/agents/actions/calculator.py`                 |
| DocumentGenerationAgent  | `src/hr_advisory/agents/actions/document_gen.py`               |
| SharedMemoryPool         | `src/hr_advisory/agents/memory/shared_pool.py`                 |
| ShortTermMemory          | `src/hr_advisory/agents/memory/short_term.py`                  |
| LongTermMemory           | `src/hr_advisory/agents/memory/long_term.py`                   |
| KB Pipeline              | `src/hr_advisory/kb/pipeline.py`                               |
| Embeddings               | `src/hr_advisory/kb/embeddings.py`                             |
| KB Validator             | `src/hr_advisory/kb/validator.py`                              |
| Citation Validator       | `src/hr_advisory/trust/citation_validator.py`                  |
| Disclaimers              | `src/hr_advisory/trust/disclaimers.py`                         |
| EATP Lineage             | `src/hr_advisory/trust/eatp_lineage.py`                        |
| CARE Governance          | `src/hr_advisory/trust/care_governance.py`                     |
| Error Correction         | `src/hr_advisory/trust/error_correction.py`                    |
| Learning Pipeline        | `src/hr_advisory/trust/learning_pipeline.py`                   |
| Accuracy Testing         | `src/hr_advisory/trust/accuracy_testing.py`                    |
| Singlish                 | `src/hr_advisory/workflows/singlish.py`                        |
| Guardrails               | `src/hr_advisory/workflows/guardrails.py`                      |
| Emergency Responses      | `src/hr_advisory/workflows/emergency_responses.py`             |
| Sector Playbooks         | `src/hr_advisory/workflows/sector_playbooks.py`                |
| Growth Triggers          | `src/hr_advisory/workflows/growth_triggers.py`                 |
| Regulatory Updates       | `src/hr_advisory/workflows/regulatory_updates.py`              |
| Compliance Checker       | `src/hr_advisory/workflows/compliance_checker.py`              |

## Appendix B: Priority Implementation Order

The weaknesses and recommendations in this analysis should be addressed in the following order based on impact:

| Priority | Item                                                                                               | Impact                                                                            |
| -------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- |
| **P0**   | Wire KB retrieval into specialist dispatch (W2)                                                    | Without this, specialists advise from training data, not from verified provisions |
| **P0**   | Enhanced specialist prompts with reasoning scaffolding and common-mistake warnings (W13, W14, W15) | Directly improves legal accuracy on every response                                |
| **P0**   | Enhanced synthesizer prompt with tone/structure/conflict resolution (W16)                          | Directly improves response quality visible to users                               |
| **P1**   | Replace Orchestrator with deterministic dispatch (W1)                                              | Removes unnecessary latency and cost                                              |
| **P1**   | Wire ComplianceAgent as mandatory post-specialist gate (W4)                                        | Catches cross-domain contradictions                                               |
| **P1**   | Wire conversation history through to specialists and synthesizer (W3)                              | Enables multi-turn coherence                                                      |
| **P1**   | Fix error handling to escalate uncertainty (W12)                                                   | Prevents silent degradation to "green"                                            |
| **P2**   | Wire anti-amnesia injection into specialist prompts (W7)                                           | Prevents drift in long conversations                                              |
| **P2**   | Add intent detection for action routing (W18-W21)                                                  | Routes calculations/documents/emergencies correctly                               |
| **P2**   | Connect citation validator to DataFlow KB (W8)                                                     | Makes citation validation dynamic                                                 |
| **P2**   | Wire trust lineage recording into pipeline (W6)                                                    | Enables audit trail and accountability                                            |
| **P3**   | Add PDPAAgent (W10)                                                                                | Closes data protection coverage gap                                               |
| **P3**   | Add GeneralHRAgent (W11)                                                                           | Handles queries not specific to any act                                           |
| **P3**   | Wire LongTermMemory enrichment (W5)                                                                | Enables company-specific personalization                                          |
| **P3**   | Source rate tables from KB (W9)                                                                    | Single source of truth for numerical thresholds                                   |
| **P3**   | Add QueryClarifierAgent                                                                            | Handles ambiguous queries gracefully                                              |
| **P4**   | Expand regression test suite to 200+ scenarios                                                     | Enables comprehensive quality monitoring                                          |
| **P4**   | Wire feedback loop to learning pipeline                                                            | Enables continuous improvement                                                    |
| **P4**   | Add few-shot examples to all prompts (W17)                                                         | Improves output consistency                                                       |
