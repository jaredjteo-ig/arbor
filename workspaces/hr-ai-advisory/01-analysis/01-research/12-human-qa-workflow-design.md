# Human QA Workflow and Automated Instruction Fine-Tuning System

**Date**: 2026-03-12
**Status**: Proposed
**Scope**: Phase 2 — Quality assurance loop and continuous agent improvement

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [QA Reviewer Interface](#2-qa-reviewer-interface)
3. [Feedback-to-Improvement Pipeline](#3-feedback-to-improvement-pipeline)
4. [Instruction Fine-Tuning Approach](#4-instruction-fine-tuning-approach)
5. [Metrics Dashboard Design](#5-metrics-dashboard-design)
6. [User Flow — QA Reviewer Session](#6-user-flow--qa-reviewer-session)
7. [Data Models](#7-data-models)
8. [API Endpoints](#8-api-endpoints)
9. [Implementation Priorities](#9-implementation-priorities)

---

## 1. System Overview

### Problem

The AITE advisory pipeline (QueryAnalyzer -> Orchestrator -> Specialists -> ResponseSynthesizer) produces responses whose quality depends on the system prompts in each agent's `_generate_system_prompt()` method. Currently, improving these prompts is a manual process: someone notices an error, a developer edits the Python file, and the change ships with the next deployment. There is no structured way to:

- Evaluate advisory quality across multiple dimensions
- Identify patterns in failures
- Update agent instructions based on evidence
- Verify that changes actually improve output quality
- Roll back changes that make things worse

### Solution Architecture

```
                        QA REVIEWER SESSION
                               |
                    +----------+----------+
                    |                     |
            [Conversation        [Evaluation
              Browser]             Form]
                    |                     |
                    +----------+----------+
                               |
                        QA Session Record
                               |
                    +----------+----------+
                    |                     |
            [Pattern             [Failure
             Detector]           Classifier]
                    |                     |
                    +----------+----------+
                               |
                    Instruction Mutation Candidates
                               |
                    +----------+----------+
                    |                     |
            [Automated           [Before/After
             Re-Run]              Comparison]
                    |                     |
                    +----------+----------+
                               |
                  +---YES---[Score       NO---+
                  |          Improved?]       |
                  |                           |
            [Promote to              [Rollback +
             Production]              Archive]
                  |                           |
                  +----------+----------+-----+
                             |
                      Metrics Dashboard
                      (trend over time)
```

### Key Design Principles

1. **Human-on-the-loop, not human-in-the-loop.** The system proposes changes; humans approve or reject. The QA reviewer never manually edits system prompts.

2. **Every change is testable.** No instruction change ships without running against the same scenarios that revealed the problem.

3. **Rollback is automatic.** If scores drop, the previous instructions are restored without human intervention.

4. **Sessions, not trickles.** QA happens in structured sessions with clear start/end points and summary reports — not as ad-hoc one-off reviews.

5. **Evidence over intuition.** Pattern detection uses frequency analysis and clustering, not gut feelings about what is "wrong."

---

## 2. QA Reviewer Interface

The QA interface is a new tab within the existing Admin page (`/admin`), added alongside Overview, Regulatory Updates, KB Management, Feedback Review, and Audit.

### 2.1 QA Sessions Tab — Session List View

**Purpose**: Show all QA sessions (past and active) and allow starting new ones.

**Layout**: Full-width card list, sorted by date descending.

```
+------------------------------------------------------------------+
| QA Sessions                                          [Start New] |
|                                                                  |
| Active Session                                                   |
| +--------------------------------------------------------------+ |
| | Session #QA-2026-03-12-001                  Started 2:15 PM  | |
| | Reviewer: Sarah Lim                                          | |
| | Progress: 8 of 24 conversations reviewed                    | |
| | Filters: amber + red risk tier, last 7 days                 | |
| | [Continue Reviewing]                        [End Session]    | |
| +--------------------------------------------------------------+ |
|                                                                  |
| Completed Sessions                                               |
| +--------------------------------------------------------------+ |
| | Session #QA-2026-03-05-001         Completed 5 Mar, 4:30 PM  | |
| | Reviewer: James Tan              14 conversations reviewed   | |
| | Overall Score: 3.8 / 5.0          2 instruction patches      | |
| | [View Summary]              [View Instruction Changes]       | |
| +--------------------------------------------------------------+ |
| +--------------------------------------------------------------+ |
| | Session #QA-2026-02-26-001         Completed 26 Feb, 3:00 PM | |
| | Reviewer: Sarah Lim              22 conversations reviewed   | |
| | Overall Score: 3.5 / 5.0          1 instruction patch        | |
| | [View Summary]              [View Instruction Changes]       | |
| +--------------------------------------------------------------+ |
+------------------------------------------------------------------+
```

**Start New Session dialog**: When the reviewer clicks "Start New," a dialog appears with filter options:

- **Date range**: Last 7 / 14 / 30 days, or custom range
- **Risk tier filter**: Green / Amber / Red (multi-select)
- **Domain filter**: Employment Act / CPF / Foreign Manpower / Fair Employment / Tax / WSH / Compliance (multi-select)
- **Flagged only**: Toggle to show only conversations that received negative user feedback
- **Confidence range**: Slider (0.0 to 1.0) to focus on low-confidence responses
- **Sampling strategy**: All matching / Random sample (with count) / Worst-performers-first

The system pre-populates a queue of conversations matching these filters.

### 2.2 Conversation Browser

**Purpose**: List conversations in the QA queue with enough context to triage without opening each one.

**Layout**: Two-panel layout. Left panel: conversation list. Right panel: selected conversation detail.

```
+---------------------------+------------------------------------------+
| QA Queue (8/24 done)      | Conversation #ADV-2026-03-10-0042        |
|                           |                                          |
| [x] #ADV..0038  3.2  Amb | User: Can I deduct salary for late       |
| [x] #ADV..0039  4.1  Grn |       coming?                            |
| [x] #ADV..0040  2.8  Red | Company: TechCo Pte Ltd (12 employees,   |
| [x] #ADV..0041  3.5  Amb |          IT sector, 3 foreign workers)    |
| [ ] #ADV..0042  --   Amb | Risk Tier: Amber                         |
| [ ] #ADV..0043  --   Red | Domains: employment_act                  |
| [ ] #ADV..0044  --   Grn | Confidence: 0.72                         |
| [ ] #ADV..0045  --   Amb | User Feedback: Thumbs Down (inaccurate)  |
|     ...                   | Turns: 3                                 |
|                           |                                          |
| Legend:                   |------------------------------------------|
| [x] = reviewed            | Turn 1 — User                           |
| Score | Risk Tier          | "Can I deduct salary for late coming?"   |
|                           |                                          |
|                           | Turn 1 — AITE                            |
|                           | "Under the Employment Act, an employer   |
|                           |  may make authorised deductions from an  |
|                           |  employee's salary, but salary deduction |
|                           |  for lateness is only permitted if..."   |
|                           | Cited: EA s.27, EA s.31                  |
|                           | Confidence: 0.72 | Risk: Amber           |
|                           |                                          |
|                           | [Specialist Outputs]  [Trust Chain]      |
|                           |                                          |
|                           | Turn 2 — User                            |
|                           | "What if it's in the employment          |
|                           |  contract?"                              |
|                           |                                          |
|                           | Turn 2 — AITE                            |
|                           | "Even if salary deduction for lateness   |
|                           |  is written in the contract, the EA      |
|                           |  limits total deductions to..."          |
|                           | Cited: EA s.27(1), EA s.27A             |
|                           |                                          |
|                           |              [Evaluate This Response]    |
+---------------------------+------------------------------------------+
```

**Key interaction patterns**:

- Clicking "Specialist Outputs" expands a collapsible section showing the raw output from each specialist agent that contributed, including the domain, confidence score, cited provisions, and cross-domain flags.
- Clicking "Trust Chain" shows the EATP genesis record and agent attestation chain for that turn.
- Clicking "Evaluate This Response" opens the evaluation form for that specific turn.
- The conversation list shows a checkmark, the score given, and the risk tier for already-reviewed items. Unreviewed items show `--` for score.

### 2.3 Response Evaluation Form

**Purpose**: Structured rubric for evaluating a single advisory response (one turn).

**Layout**: Modal or right-panel overlay. The response text remains visible above/alongside the form.

**Evaluation Dimensions** (each rated 1-5):

| Dimension                 | 1 (Poor)                                    | 3 (Adequate)                                           | 5 (Excellent)                                            |
| ------------------------- | ------------------------------------------- | ------------------------------------------------------ | -------------------------------------------------------- |
| **Legal Accuracy**        | Factually wrong; states incorrect law       | Correct in broad strokes but misses nuances            | Precise, comprehensive, addresses edge cases             |
| **Citation Quality**      | Missing citations or cites wrong provisions | Citations present but incomplete or vague              | Every claim backed by correct provision with section     |
| **Relevance**             | Answer does not address the question asked  | Addresses the question but with unnecessary tangents   | Directly and completely addresses the user's question    |
| **Actionability**         | User cannot act on this advice              | User can act but needs significant additional guidance | Clear next steps the user can immediately follow         |
| **Context Usage**         | Ignores company context entirely            | Partially uses company context                         | Fully tailors advice to company size, sector, worker mix |
| **Conversation Tracking** | Loses context from prior turns              | Partially tracks prior turns                           | Seamlessly builds on prior conversation context          |
| **Tone and Clarity**      | Jargon-heavy, condescending, or unclear     | Understandable but could be clearer                    | Plain language, appropriate for SME owner audience       |

```
+------------------------------------------------------------------+
| Evaluate Response — Turn 2 of #ADV-2026-03-10-0042               |
|                                                                  |
| Legal Accuracy        [1] [2] [3] [4] [5]     Selected: 3       |
| Citation Quality      [1] [2] [3] [4] [5]     Selected: 4       |
| Relevance             [1] [2] [3] [4] [5]     Selected: 4       |
| Actionability         [1] [2] [3] [4] [5]     Selected: 2       |
| Context Usage         [1] [2] [3] [4] [5]     Selected: 3       |
| Conversation Tracking [1] [2] [3] [4] [5]     Selected: 5       |
| Tone and Clarity      [1] [2] [3] [4] [5]     Selected: 4       |
|                                                                  |
| --- Citation Flags ---                                           |
|                                                                  |
| Cited Provisions:                                                |
|   [x] EA s.27(1) — Correct and relevant                         |
|   [ ] EA s.27A   — Incorrect: should be EA s.27(2)(a)           |
|                     [Enter correct reference: _____________ ]    |
|   [+] Add missing citation                                      |
|                                                                  |
| --- Correction ---                                               |
|                                                                  |
| Is this response materially incorrect?  [Yes] [No]               |
|                                                                  |
| If yes, what is the correct answer?                              |
| +--------------------------------------------------------------+ |
| | The EA s.27 deduction cap of 50% applies to the total of     | |
| | ALL authorised deductions in any one salary period, not to   | |
| | each individual deduction. The response incorrectly states   | |
| | that each deduction type is capped at 50%. Additionally,     | |
| | the response should mention that Part IV employees have      | |
| | additional protections under s.31...                         | |
| +--------------------------------------------------------------+ |
|                                                                  |
| Failure Category (if score < 3 on any dimension):                |
|   ( ) Wrong law cited                                            |
|   ( ) Correct law but wrong interpretation                       |
|   (x) Missed critical nuance                                    |
|   ( ) Ignored company context                                   |
|   ( ) Lost conversation context                                 |
|   ( ) Overly generic / not actionable                           |
|   ( ) Wrong domain routing                                      |
|   ( ) Fabricated citation                                        |
|   ( ) Other: [__________________]                                |
|                                                                  |
| Affected Agent(s):                                               |
|   [x] employment_act_specialist                                  |
|   [ ] response_synthesizer                                       |
|   [ ] query_analyzer                                             |
|   [ ] orchestrator                                               |
|                                                                  |
| Notes (optional):                                                |
| +--------------------------------------------------------------+ |
| | The specialist correctly identifies s.27 but misapplies the  | |
| | aggregation rule. This is a Part IV edge case.               | |
| +--------------------------------------------------------------+ |
|                                                                  |
|                     [Save & Next]  [Save & Close]                |
+------------------------------------------------------------------+
```

### 2.4 Session Summary View

**Purpose**: At session end, display aggregate findings and trigger the improvement pipeline.

**Layout**: Full-page summary with sections.

```
+------------------------------------------------------------------+
| QA Session Summary — #QA-2026-03-12-001                          |
| Reviewer: Sarah Lim | Duration: 2h 15m | 24 conversations       |
|                                                                  |
| --- Overall Scores ---                                           |
|                                                                  |
| Dimension             Avg    Min   Trend vs Last Session         |
| Legal Accuracy        3.6    1     -0.2 (declining)              |
| Citation Quality      4.1    2     +0.3 (improving)              |
| Relevance             4.0    2     +0.1 (stable)                 |
| Actionability         3.2    1     -0.4 (declining)              |
| Context Usage         3.5    2     +0.2 (improving)              |
| Conversation Tracking 4.3    3     +0.5 (improving)              |
| Tone and Clarity      4.2    3     +0.1 (stable)                 |
|                                                                  |
| Composite Score: 3.8 / 5.0   (previous: 3.7)                    |
|                                                                  |
| --- Failure Pattern Summary ---                                  |
|                                                                  |
| Pattern                          Count  Affected Agent           |
| Missed Part IV nuance            5      employment_act           |
| Overly generic advice            4      response_synthesizer     |
| Wrong CPF age band applied       3      cpf                      |
| Fabricated citation              1      employment_act           |
| Lost conversation context        2      query_analyzer           |
|                                                                  |
| --- Flagged Citations ---                                        |
|                                                                  |
| 3 incorrect citations flagged                                    |
| 2 missing citations identified                                   |
| 0 fabricated citations (down from 2 last session)                |
|                                                                  |
| --- Material Corrections ---                                     |
|                                                                  |
| 4 responses marked as materially incorrect                       |
| 3 have correction text provided                                  |
|                                                                  |
| --- Recommended Actions ---                                      |
|                                                                  |
| The system has identified 3 instruction patch candidates:        |
|                                                                  |
| 1. [employment_act_specialist] Add Part IV aggregation rule      |
|    for salary deductions (evidence: 5 failures)                  |
|    [Preview Patch]  [Approve]  [Reject]                          |
|                                                                  |
| 2. [response_synthesizer] Add actionability checklist to         |
|    synthesis prompt (evidence: 4 failures)                       |
|    [Preview Patch]  [Approve]  [Reject]                          |
|                                                                  |
| 3. [cpf_specialist] Add age band boundary clarification          |
|    (evidence: 3 failures)                                        |
|    [Preview Patch]  [Approve]  [Reject]                          |
|                                                                  |
|          [Approve All]  [Run Automated Test Suite]               |
+------------------------------------------------------------------+
```

---

## 3. Feedback-to-Improvement Pipeline

### 3.1 Pipeline Stages

```
Stage 1: COLLECT
  QA evaluations + user feedback + citation validation failures
         |
Stage 2: CLASSIFY
  Group by failure category + affected agent + domain
         |
Stage 3: CLUSTER
  Identify recurring patterns (>= 3 occurrences = pattern)
         |
Stage 4: GENERATE
  Produce instruction mutation candidates for each pattern
         |
Stage 5: TEST
  Re-run original failing scenarios with mutated instructions
         |
Stage 6: COMPARE
  Score new outputs against original QA evaluations
         |
Stage 7: DECIDE
  Promote (scores improved) or rollback (scores same or worse)
         |
Stage 8: RECORD
  Log all decisions, diffs, and scores in audit trail
```

### 3.2 How Feedback Is Stored

Feedback flows into the system from three sources:

1. **QA evaluations** (primary) — structured rubric scores from this workflow
2. **User feedback** (secondary) — thumbs up/down from the existing `/learning/feedback` endpoint
3. **Automated validation failures** — citation validator rejections, confidence drops, constraint violations from EATP trust chain

All three sources feed into a unified `QAEvaluation` model (see Section 7) that stores:

- The conversation ID and turn number
- All seven dimension scores
- Citation flags (correct/incorrect/missing)
- Correction text
- Failure category classification
- Affected agent identification
- Reviewer identity and session ID

### 3.3 Pattern Detection

Pattern detection runs at session end and uses frequency analysis, not machine learning. This is a deliberate choice: the volume of QA evaluations is too low for ML, and rule-based detection is auditable.

**Detection rules**:

1. **Failure Frequency**: If the same failure category appears >= 3 times in a session, or >= 5 times across the last 3 sessions, it is flagged as a pattern.

2. **Agent Concentration**: If >= 60% of failures in a category are attributed to the same agent, that agent's instructions are the mutation target.

3. **Domain Concentration**: If >= 70% of failures in a category occur within the same domain, the pattern is domain-specific (not a general prompt issue).

4. **Score Regression**: If a dimension's average score drops by >= 0.5 points compared to the previous 3 sessions, the affected dimension triggers a pattern investigation even if no single failure category dominates.

5. **Citation Failure Clustering**: If the same provision is flagged as incorrect >= 2 times, or the same provision is identified as missing >= 2 times, it triggers a KB gap detection (separate from instruction fine-tuning).

**Output of pattern detection**: A list of `FailurePattern` records (see Section 7), each containing:

- Pattern description
- Failure category
- Affected agent(s)
- Affected domain(s)
- Evidence count (number of evaluations supporting this pattern)
- Example query/response pairs (up to 5)
- Suggested mutation target (which section of which agent's system prompt)

### 3.4 How Instructions Are Updated (Prompt Mutation Strategy)

The mutation strategy operates on the structured sections within each agent's `_generate_system_prompt()` method. Each specialist agent's system prompt follows a consistent structure:

```
DOMAIN CONSTRAINT: ...
EXPERTISE: ...
CITATION RULES: ...
OUTPUT: ...
```

Mutations can target three areas:

**Area 1: EXPERTISE section additions** — Adding specific rules, edge cases, or clarifications. This is the safest mutation type.

Example mutation for the "missed Part IV aggregation rule" pattern:

```
BEFORE:
  EXPERTISE:
    - Part IV protections (rest days, hours of work, overtime, holidays)
    ...

AFTER:
  EXPERTISE:
    - Part IV protections (rest days, hours of work, overtime, holidays)
    - Salary deduction limits: s.27 caps TOTAL authorised deductions at 50%
      of salary in any one period — this is an aggregate cap, not per-deduction
    ...
```

**Area 2: CITATION RULES refinements** — Adding specific citation patterns or anti-hallucination rules based on observed fabrication patterns.

**Area 3: QA-LEARNED RULES section** — A new section appended to each agent's system prompt, specifically for rules derived from QA feedback. This section is clearly delineated so it can be reviewed, modified, and rolled back independently.

```
QA-LEARNED RULES (auto-generated from QA feedback, version 12):
  - When advising on salary deductions under s.27, always clarify that the
    50% cap is aggregate across all deduction types, not per-deduction.
  - When the company has fewer than 5 employees, note that micro-SMEs may
    have additional flexibility under MOM administrative guidance.
  - When CPF contribution rates change at age boundaries (55, 60, 65, 70),
    always specify that the new rate applies from the month FOLLOWING the
    birthday month.
```

The mutation generator (a Kaizen agent using the `InstructionMutationSignature`) receives:

- The current system prompt
- The failure pattern description
- Up to 5 example query/response pairs with corrections
- The affected dimension scores

It produces:

- A proposed addition to the QA-LEARNED RULES section
- A rationale for the change
- An estimate of which evaluation dimensions should improve

### 3.5 How Improvements Are Validated

After mutations are generated, the system runs an automated validation:

1. **Collect test bank**: Gather all query/response pairs from the QA session where the pattern was observed (the "failing scenarios").

2. **Run with current instructions**: Re-run each scenario through the full advisory pipeline with the current (unmodified) system prompts. Record the outputs.

3. **Run with mutated instructions**: Re-run the same scenarios with the proposed instruction changes. Record the outputs.

4. **Score comparison**: For each scenario, compare the new output against the QA reviewer's correction text and the original evaluation scores. The comparison uses a Kaizen scoring agent (`QAScoreComparisonSignature`) that evaluates whether the new output is closer to the correction text and would likely score higher on the failing dimensions.

5. **Decision logic**:
   - If >= 80% of failing scenarios show improvement AND no previously-passing scenario regresses: **PROMOTE**
   - If < 80% improve but some improve and none regress: **PROMOTE WITH CAVEAT** (flagged for human review)
   - If any previously-passing scenario regresses: **REJECT** (the change makes something worse)
   - If no scenarios improve: **REJECT** (the change is ineffective)

6. **Human approval gate**: Even when the system recommends PROMOTE, the QA reviewer sees the before/after comparison and must click "Approve" before the change goes live.

---

## 4. Instruction Fine-Tuning Approach

### 4.1 What Can Be Safely Mutated

| Component                                               | Mutable? | Risk   | Approach                                                                            |
| ------------------------------------------------------- | -------- | ------ | ----------------------------------------------------------------------------------- |
| `_generate_system_prompt()` — EXPERTISE section         | Yes      | Low    | Append clarifications and edge-case rules                                           |
| `_generate_system_prompt()` — CITATION RULES            | Yes      | Low    | Add specific citation format rules                                                  |
| `_generate_system_prompt()` — DOMAIN CONSTRAINT         | No       | High   | Domain boundaries are architectural; changing them could cause cross-domain leakage |
| `_generate_system_prompt()` — OUTPUT format             | No       | High   | Output schema changes break downstream parsing in `_base.py`                        |
| Signature docstrings                                    | Cautious | Medium | Can add `__guidelines__` entries; cannot change field definitions                   |
| `SpecialistConfig` parameters (temperature, max_tokens) | Cautious | Medium | Temperature changes affect determinism; must be carefully tested                    |
| `ResponseSynthesizerAgent` prompt — RULES section       | Yes      | Low    | Add actionability and clarity rules                                                 |
| `QueryAnalyzerAgent` prompt — classification rules      | Cautious | Medium | Changes affect routing, which affects all downstream outputs                        |
| `OrchestratorAgent` prompt — dispatch rules             | Cautious | Medium | Changes affect which specialists are invoked                                        |

### 4.2 Prompt Structure for Easy Patching

Each specialist agent's system prompt should be restructured into clearly tagged sections. This is a one-time migration that makes automated patching safe and auditable.

**Current structure** (monolithic string in `_generate_system_prompt()`):

```python
def _generate_system_prompt(self) -> str:
    return (
        "You are a Singapore Employment Act specialist.\n\n"
        "DOMAIN CONSTRAINT: ...\n\n"
        "EXPERTISE:\n  - ...\n\n"
        "CITATION RULES:\n  - ...\n\n"
        "OUTPUT: ..."
    )
```

**Proposed structure** (sectioned with version-controlled QA rules):

```python
def _generate_system_prompt(self) -> str:
    base_prompt = (
        "You are a Singapore Employment Act specialist.\n\n"
        "DOMAIN CONSTRAINT: ...\n\n"
        "EXPERTISE:\n  - ...\n\n"
        "CITATION RULES:\n  - ...\n\n"
        "OUTPUT: ..."
    )
    qa_rules = self._get_qa_learned_rules()
    return f"{base_prompt}\n\n{qa_rules}"

def _get_qa_learned_rules(self) -> str:
    """Load QA-learned rules from the instruction store.

    Returns empty string if no rules exist yet.
    Rules are versioned and can be rolled back independently.
    """
    rules = InstructionStore.get_rules(
        agent_id=self.agent_id,
        version="current"
    )
    if not rules:
        return ""
    return (
        f"QA-LEARNED RULES (v{rules.version}, "
        f"last updated {rules.updated_at}):\n"
        + "\n".join(f"  - {r}" for r in rules.rules)
    )
```

### 4.3 A/B Testing Prompt Variations

Full A/B testing with live traffic is not appropriate for legal advisory (you cannot serve potentially worse advice to half your users). Instead, the system uses a **shadow testing** approach:

1. **Shadow pipeline**: Run every live query through both the current and candidate instructions in parallel. The user always sees the current-instruction output.

2. **Shadow scoring**: The candidate output is stored and scored offline by the QA scoring agent against the same criteria.

3. **Shadow metrics**: After accumulating >= 50 shadow-scored responses, compare aggregate dimension scores between current and candidate.

4. **Promotion decision**: If the candidate consistently outperforms current on the target dimensions without regression on others, promote to production.

This approach is compute-expensive (doubles inference cost during testing), so it should only be used for high-impact changes. For most QA-driven patches, the replay-and-compare method from Section 3.5 is sufficient.

### 4.4 Rollback Strategy

Every instruction change is stored as a versioned record in the `InstructionVersion` model (Section 7). Rollback is straightforward:

1. **Automatic rollback trigger**: If the automated monitoring detects a score regression >= 0.3 points on any dimension over a 48-hour window after an instruction change, the system automatically reverts to the previous version and alerts the QA reviewer.

2. **Manual rollback**: The QA reviewer can revert any instruction change from the Session Summary view at any time. One click: "Revert to version N."

3. **Version history**: All versions are retained indefinitely. The QA reviewer can inspect the diff between any two versions, see which QA session produced each version, and see the test results that justified each change.

4. **Rollback scope**: Each agent's QA-LEARNED RULES section is versioned independently. Rolling back the Employment Act specialist does not affect the CPF specialist.

---

## 5. Metrics Dashboard Design

### 5.1 What to Measure

**Primary metrics** (shown on the dashboard):

| Metric                      | Source                  | Visualization                                  |
| --------------------------- | ----------------------- | ---------------------------------------------- |
| Composite quality score     | QA evaluations          | Line chart over time (weekly)                  |
| Per-dimension scores        | QA evaluations          | Radar chart (current vs previous session)      |
| Failure pattern frequency   | Pattern detection       | Stacked bar chart by category                  |
| Citation accuracy rate      | QA citation flags       | Percentage with trend line                     |
| Material correction rate    | QA corrections          | Percentage of responses marked incorrect       |
| Instruction version count   | Instruction store       | Number by agent (shows improvement velocity)   |
| Test pass rate              | Automated re-runs       | Percentage of test bank scenarios passing      |
| User satisfaction rate      | User feedback           | Thumbs-up percentage with trend line           |
| Score improvement per patch | Before/after comparison | Bar chart showing delta per instruction change |

**Secondary metrics** (available on drill-down):

| Metric                              | Source                         |
| ----------------------------------- | ------------------------------ |
| Average QA session duration         | Session records                |
| Conversations reviewed per session  | Session records                |
| Time to review per conversation     | Session records                |
| Pattern recurrence rate             | Cross-session pattern analysis |
| Rollback frequency                  | Instruction version history    |
| Shadow test sample size and results | Shadow pipeline                |

### 5.2 Dashboard Layout

The metrics dashboard is a dedicated view within the QA Sessions tab, accessible via a "Metrics" sub-tab.

```
+------------------------------------------------------------------+
| QA Metrics Dashboard                        Period: [Last 90 days]|
|                                                                  |
| --- Headline Numbers ---                                         |
| +--------+ +--------+ +--------+ +--------+ +--------+          |
| |  3.8   | |  92%   | |   4%   | |   12   | |  87%   |          |
| |Composite| |Citation| |Material| |Patches | |User    |          |
| | Score   | |Accuracy| |Errors  | |Applied | |Satisf. |          |
| | +0.3   | | +4%    | | -2%    | |        | | +5%    |          |
| +--------+ +--------+ +--------+ +--------+ +--------+          |
|                                                                  |
| --- Quality Score Over Time ---                                  |
| [Line chart: x-axis = QA session date, y-axis = 1.0-5.0]        |
| [7 lines, one per dimension, with composite as bold line]        |
| [Vertical markers for each instruction patch deployment]         |
|                                                                  |
| --- Dimension Comparison (Current vs Previous Session) ---       |
| [Radar chart with 7 axes]                                        |
| [Current session in blue, previous in gray]                      |
|                                                                  |
| --- Failure Patterns by Category ---                             |
| [Stacked bar chart: x-axis = session, y-axis = count]           |
| [Each bar segment = failure category]                            |
| [Declining stacks = improvement]                                 |
|                                                                  |
| --- Instruction Patch Impact ---                                 |
| +--------------------------------------------------------------+ |
| | Patch                  Before  After   Delta  Status          | |
| | EA: Part IV deductions  2.8     4.1    +1.3   Promoted       | |
| | RS: Actionability rule  3.0     3.4    +0.4   Promoted       | |
| | CPF: Age band boundary  2.5     4.2    +1.7   Promoted       | |
| | EA: Probation notice    3.8     3.6    -0.2   Rolled back    | |
| +--------------------------------------------------------------+ |
|                                                                  |
| --- Test Bank Performance ---                                    |
| [Bar chart: x-axis = agent, y-axis = pass rate %]               |
| [Pass = score >= 3.5 on all dimensions]                          |
| [Shows current pass rate vs baseline (first session)]            |
+------------------------------------------------------------------+
```

### 5.3 Baseline Establishment

The first QA session establishes the baseline. All subsequent sessions are compared against it:

- **Absolute baseline**: The dimension scores from Session 1 become the floor. The system tracks cumulative improvement from this baseline.
- **Rolling baseline**: The previous 3 sessions establish the recent baseline. Score regressions are measured against this rolling window, not just the absolute baseline.
- **Per-agent baseline**: Each agent has its own baseline, because some agents (Employment Act) handle more complex queries than others (Tax).

### 5.4 Trend Detection

The dashboard highlights trends using simple rules:

- **Improving**: Average score increased >= 0.2 over last 3 sessions
- **Stable**: Average score changed < 0.2 over last 3 sessions
- **Declining**: Average score decreased >= 0.2 over last 3 sessions
- **Significantly declining**: Average score decreased >= 0.5 — triggers an alert

---

## 6. User Flow — QA Reviewer Session

### Step-by-step narrative

**Context**: Sarah Lim is an HR domain expert who conducts weekly QA reviews. Today is Wednesday, her regular QA day.

---

**Step 1: Start session**

Sarah navigates to Admin > QA Sessions and clicks "Start New." She selects:

- Date range: Last 7 days
- Risk tier: Amber and Red only (she focuses on higher-risk responses)
- Domain: All
- Sampling: Worst-performers-first (lowest confidence first)

The system finds 24 conversations matching her filters and creates a QA queue.

---

**Step 2: Review first conversation**

Sarah clicks the first conversation in the queue. It shows a 3-turn conversation about salary deductions for lateness. She reads the full exchange, including the original user question, the AI response, and two follow-up turns.

She notices the response correctly identifies EA s.27 but misapplies the aggregation rule for the 50% deduction cap. She clicks "Evaluate This Response" on Turn 2.

---

**Step 3: Fill evaluation form**

Sarah rates each dimension:

- Legal Accuracy: 3 (correct law, wrong interpretation)
- Citation Quality: 4 (correct citations, could add s.27(2)(a))
- Relevance: 4
- Actionability: 2 (the wrong interpretation makes the advice non-actionable)
- Context Usage: 3 (does not consider the company has only 12 employees)
- Conversation Tracking: 5 (properly tracks the follow-up about contract terms)
- Tone and Clarity: 4

She flags the EA s.27A citation as incorrect (should be s.27(2)(a)), adds the missing citation for s.31, and selects "Missed critical nuance" as the failure category. She marks the response as materially incorrect and types the correct interpretation in the correction field.

She clicks "Save & Next."

---

**Step 4: Continue through the queue**

Sarah works through the remaining conversations. Most take 3-5 minutes each. She evaluates 24 conversations in about 2 hours, marking 4 as materially incorrect.

---

**Step 5: End session**

Sarah clicks "End Session." The system immediately runs pattern detection and presents the Session Summary.

She sees that "Missed Part IV nuance" appeared 5 times, all attributed to the employment_act_specialist. "Overly generic advice" appeared 4 times, attributed to the response_synthesizer. "Wrong CPF age band" appeared 3 times.

---

**Step 6: Review instruction patch candidates**

The system has generated 3 instruction patch candidates. Sarah clicks "Preview Patch" on the first one (Employment Act Part IV aggregation rule).

She sees:

**Current instruction excerpt**:

```
EXPERTISE:
  - Part IV protections (rest days, hours of work, overtime, holidays)
  - Leave entitlements (annual, sick, maternity, paternity, childcare)
  ...
```

**Proposed addition to QA-LEARNED RULES**:

```
QA-LEARNED RULES (v3):
  - When advising on salary deductions under EA s.27, always specify that
    the 50% cap applies to the AGGREGATE of all authorised deductions in
    any one salary period, not to each individual deduction type. This is
    a common misinterpretation. Cite s.27(1) for the cap and s.27(2)(a)
    for the enumeration of permitted deductions.
  [... existing rules from v2 ...]
```

Sarah reads the proposed rule, confirms it is legally correct, and clicks "Approve."

---

**Step 7: Automated test run**

After Sarah approves all 3 patches, she clicks "Run Automated Test Suite." The system:

1. Collects the 15 failing scenarios from this session (5 for Part IV, 4 for actionability, 3 for CPF age bands, 3 others)
2. Runs each scenario through the pipeline with current instructions (baseline)
3. Runs each scenario through the pipeline with the proposed patches
4. Compares the outputs using the QA scoring agent

This takes approximately 5-10 minutes. Sarah can leave the page; she will get a notification when results are ready.

---

**Step 8: Review test results**

Sarah returns to see the test results:

```
Patch 1 (EA Part IV deductions):
  5/5 failing scenarios improved (avg +1.3 on Legal Accuracy)
  0 regressions on passing scenarios
  Recommendation: PROMOTE

Patch 2 (Actionability checklist):
  3/4 failing scenarios improved (avg +0.4 on Actionability)
  0 regressions
  Recommendation: PROMOTE

Patch 3 (CPF age band boundary):
  3/3 failing scenarios improved (avg +1.7 on Legal Accuracy)
  0 regressions
  Recommendation: PROMOTE
```

Sarah clicks "Promote All" to deploy the updated instructions.

---

**Step 9: Verify on dashboard**

Sarah navigates to the Metrics sub-tab. She sees the composite score has moved from 3.5 (baseline) to 3.8 (this session). The "Instruction Patch Impact" table shows her 3 patches with their before/after scores. The failure pattern chart shows "Missed Part IV nuance" declining from 8 (session 1) to 5 (this session), with the expectation it will drop further now that the patch is deployed.

---

## 7. Data Models

These models extend the existing learning pipeline (`src/hr_advisory/trust/learning_pipeline.py`). They follow the same in-memory pattern for development, backed by DataFlow models in production.

### QA Session

```python
@dataclass
class QASession:
    """A structured QA review session."""
    session_id: str
    reviewer_id: str
    reviewer_email: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    status: str = "active"  # active, completed, abandoned
    filters: dict = field(default_factory=dict)  # date_range, risk_tier, domains, etc.
    conversation_ids: list[str] = field(default_factory=list)  # queued conversations
    evaluations_completed: int = 0
    composite_score: Optional[float] = None
    summary: Optional[dict] = None  # generated at session end
```

### QA Evaluation

```python
@dataclass
class QAEvaluation:
    """Evaluation of a single advisory response (one turn)."""
    evaluation_id: str
    session_id: str
    conversation_id: str
    turn_number: int
    reviewer_id: str

    # Dimension scores (1-5)
    legal_accuracy: int
    citation_quality: int
    relevance: int
    actionability: int
    context_usage: int
    conversation_tracking: int
    tone_and_clarity: int

    # Citation flags
    citation_flags: list[dict] = field(default_factory=list)
    # Each: {"provision_id": str, "status": "correct"|"incorrect"|"missing",
    #         "correction": Optional[str]}

    # Correction
    is_materially_incorrect: bool = False
    correction_text: str = ""

    # Classification
    failure_category: Optional[str] = None
    affected_agents: list[str] = field(default_factory=list)

    # Metadata
    notes: str = ""
    evaluated_at: datetime = field(default_factory=datetime.now)

    @property
    def composite_score(self) -> float:
        scores = [
            self.legal_accuracy, self.citation_quality,
            self.relevance, self.actionability,
            self.context_usage, self.conversation_tracking,
            self.tone_and_clarity,
        ]
        return sum(scores) / len(scores)

    @property
    def has_failures(self) -> bool:
        return any(s < 3 for s in [
            self.legal_accuracy, self.citation_quality,
            self.relevance, self.actionability,
            self.context_usage, self.conversation_tracking,
            self.tone_and_clarity,
        ])
```

### Failure Pattern

```python
@dataclass
class FailurePattern:
    """A detected pattern of failures across evaluations."""
    pattern_id: str
    session_id: str  # session where this pattern was detected
    description: str
    failure_category: str
    affected_agents: list[str]
    affected_domains: list[str]
    evidence_count: int
    example_evaluations: list[str]  # evaluation_ids
    suggested_mutation_target: str  # e.g., "employment_act_specialist.qa_learned_rules"
    status: str = "detected"  # detected, mutation_generated, testing, promoted, rejected
    detected_at: datetime = field(default_factory=datetime.now)
```

### Instruction Version

```python
@dataclass
class InstructionVersion:
    """A versioned snapshot of an agent's QA-learned rules."""
    version_id: str
    agent_id: str  # e.g., "employment_act_specialist"
    version_number: int
    rules: list[str]  # the QA-learned rules (ordered list of rule strings)
    created_from_session: str  # QA session ID that produced this version
    created_from_patterns: list[str]  # pattern IDs that motivated this version

    # Test results
    test_results: Optional[dict] = None  # {scenario_id: {before: score, after: score}}
    scenarios_improved: int = 0
    scenarios_regressed: int = 0

    # Lifecycle
    status: str = "candidate"  # candidate, testing, promoted, rolled_back
    promoted_at: Optional[datetime] = None
    rolled_back_at: Optional[datetime] = None
    promoted_by: Optional[str] = None

    created_at: datetime = field(default_factory=datetime.now)

    @property
    def is_current(self) -> bool:
        return self.status == "promoted" and self.rolled_back_at is None
```

### Test Scenario

```python
@dataclass
class TestScenario:
    """A test scenario in the test bank, derived from QA evaluations."""
    scenario_id: str
    source_conversation_id: str
    source_turn_number: int
    source_evaluation_id: str

    # The test inputs
    query_text: str
    company_context: dict
    conversation_history: Optional[str] = None

    # The expected behavior (from QA evaluation)
    correction_text: str = ""
    expected_dimensions: dict = field(default_factory=dict)
    # e.g., {"legal_accuracy": 4, "actionability": 4}

    # Categorization
    domain: str = ""
    failure_category: str = ""
    affected_agent: str = ""

    # Results tracking
    current_score: Optional[float] = None
    last_tested: Optional[datetime] = None

    created_at: datetime = field(default_factory=datetime.now)
```

---

## 8. API Endpoints

These endpoints extend the existing `/learning/` router.

### QA Session Management

```
POST   /learning/qa/sessions                    Start a new QA session
GET    /learning/qa/sessions                    List all QA sessions
GET    /learning/qa/sessions/{id}               Get session details
POST   /learning/qa/sessions/{id}/end           End a session (triggers pattern detection)
GET    /learning/qa/sessions/{id}/queue          Get conversation queue for session
GET    /learning/qa/sessions/{id}/summary        Get session summary
```

### Evaluations

```
POST   /learning/qa/evaluations                 Submit an evaluation
GET    /learning/qa/evaluations?session_id=X     List evaluations for a session
GET    /learning/qa/evaluations/{id}             Get evaluation details
PUT    /learning/qa/evaluations/{id}             Update an evaluation
```

### Patterns and Mutations

```
GET    /learning/qa/patterns?session_id=X        List failure patterns for a session
GET    /learning/qa/patterns/{id}                Get pattern details
POST   /learning/qa/patterns/{id}/generate       Generate instruction mutation
GET    /learning/qa/mutations/{id}/preview        Preview mutation diff
POST   /learning/qa/mutations/{id}/approve        Approve mutation
POST   /learning/qa/mutations/{id}/reject         Reject mutation
```

### Instruction Versions

```
GET    /learning/qa/instructions/{agent_id}      Get current instruction version
GET    /learning/qa/instructions/{agent_id}/history  List all versions
POST   /learning/qa/instructions/{agent_id}/test     Run test suite
GET    /learning/qa/instructions/{agent_id}/test/{run_id}  Get test results
POST   /learning/qa/instructions/{agent_id}/promote  Promote candidate version
POST   /learning/qa/instructions/{agent_id}/rollback Roll back to previous version
```

### Metrics

```
GET    /learning/qa/metrics                      Get aggregate QA metrics
GET    /learning/qa/metrics/dimensions            Per-dimension trends
GET    /learning/qa/metrics/patches               Instruction patch impact
GET    /learning/qa/metrics/test-bank              Test bank pass rates
```

All endpoints require `owner` or `hr_manager` role (using the existing `require_role` middleware).

---

## 9. Implementation Priorities

### Phase 2a: Foundation (Week 1-2)

1. Data models (`QASession`, `QAEvaluation`, `FailurePattern`, `InstructionVersion`, `TestScenario`)
2. QA session management endpoints (start, end, queue)
3. Evaluation submission endpoint
4. QA Sessions tab in admin interface (session list, conversation browser)
5. Evaluation form component

### Phase 2b: Pattern Detection (Week 3)

6. Pattern detection engine (frequency analysis, agent concentration, domain concentration)
7. Session summary generation
8. Session summary view in admin interface
9. Failure pattern display

### Phase 2c: Instruction Mutation (Week 4)

10. Restructure all specialist agent prompts into sectioned format with `_get_qa_learned_rules()`
11. `InstructionStore` module for reading/writing versioned QA rules
12. Instruction mutation generator (Kaizen agent with `InstructionMutationSignature`)
13. Mutation preview and approval UI

### Phase 2d: Automated Testing (Week 5)

14. Test bank management (scenarios derived from evaluations)
15. Automated re-run pipeline (run scenarios with current vs. candidate instructions)
16. QA scoring agent (`QAScoreComparisonSignature`)
17. Test results display and promotion/rollback UI
18. Automatic rollback trigger (score regression monitoring)

### Phase 2e: Metrics Dashboard (Week 6)

19. Metrics aggregation endpoints
20. Dashboard components (line charts, radar chart, bar charts)
21. Trend detection and alerting
22. Baseline establishment logic

---

## Appendix A: Integration with Existing Systems

### Existing Learning Pipeline

The QA workflow does NOT replace the existing learning pipeline (`src/hr_advisory/trust/learning_pipeline.py`). It extends it:

- **User feedback** (thumbs up/down) continues to flow through `/learning/feedback` and feeds into KB gap detection.
- **QA evaluations** are a higher-fidelity signal that feeds into instruction fine-tuning (the new capability).
- **Monthly reports** (`generate_monthly_report`) will be extended to include QA metrics alongside existing feedback metrics.
- **Recommendations** generated by the learning pipeline (`propose_recommendation` with type `PROMPT_REFINEMENT`) will link to QA-generated instruction versions.

### Existing Admin Interface

The QA Sessions tab is added as a new tab alongside the existing 5 tabs in `/admin/page.tsx`:

```typescript
type TabId = "overview" | "updates" | "kb" | "feedback" | "qa" | "audit";

const TABS: TabDef[] = [
  // ... existing tabs ...
  { id: "qa", label: "QA Sessions", icon: ClipboardCheck },
  // ... audit tab ...
];
```

### Existing Trust Infrastructure

QA evaluations reference the EATP trust chain:

- The `GenesisRecord` from each advisory session provides the system state at query time (KB currency, company profile completeness, agent versions).
- The `AgentAttestation` records show which agents contributed to each response and with what confidence.
- When QA reviewers identify that a failure was caused by a KB gap (not an instruction issue), this feeds into `detect_kb_gap()` rather than instruction mutation.

### Existing Advisory Pipeline

The advisory pipeline (`src/hr_advisory/api/routers/advisory.py`) does not change. The QA system reads from the advisory session records (conversation history, specialist outputs, trust chain) but does not modify the pipeline itself. Instruction changes take effect through the agent's `_get_qa_learned_rules()` method, which is called each time `_generate_system_prompt()` runs.

---

## Appendix B: Failure Category Taxonomy

These categories are used in the evaluation form and pattern detection. They align with the existing `FeedbackCategory` enum but provide finer granularity:

| Category                           | Description                                  | Typical Root Cause                                   | Mutation Target           |
| ---------------------------------- | -------------------------------------------- | ---------------------------------------------------- | ------------------------- |
| `wrong_law_cited`                  | Cites a provision that does not apply        | Specialist system prompt missing domain boundary     | EXPERTISE section         |
| `correct_law_wrong_interpretation` | Cites correct provision but misinterprets it | Missing edge-case rule in specialist prompt          | QA-LEARNED RULES          |
| `missed_critical_nuance`           | Broadly correct but misses important detail  | Specialist prompt too general                        | QA-LEARNED RULES          |
| `ignored_company_context`          | Does not use company profile information     | Specialist prompt does not emphasize context usage   | QA-LEARNED RULES          |
| `lost_conversation_context`        | Does not track prior turns properly          | QueryAnalyzer history handling                       | QueryAnalyzer prompt      |
| `overly_generic`                   | Correct but too general to be useful         | ResponseSynthesizer prompt lacks actionability rules | ResponseSynthesizer RULES |
| `wrong_domain_routing`             | Query routed to wrong specialist             | QueryAnalyzer domain detection keywords              | QueryAnalyzer STEP 1      |
| `fabricated_citation`              | Cites a provision that does not exist        | Specialist citation rules insufficient               | CITATION RULES section    |
| `outdated_information`             | Cites correct provision but uses old data    | KB gap (not an instruction issue)                    | KB update, not prompt     |
| `other`                            | Does not fit other categories                | Varies                                               | Manual assessment         |

---

## Appendix C: Security and Access Control

- All QA endpoints require `owner` or `hr_manager` role via the existing `require_role` middleware.
- QA evaluations are append-only (can be updated but not deleted) for audit trail integrity.
- Instruction versions are immutable once created. Rollback creates a new version pointing to the old rules, it does not delete the rolled-back version.
- Correction text may contain sensitive HR scenarios. It is stored with the same access controls as advisory session data (tenant-isolated, encrypted at rest).
- The instruction mutation generator agent has a constraint envelope: it can ONLY append to QA-LEARNED RULES. It cannot modify DOMAIN CONSTRAINT, OUTPUT format, or the base EXPERTISE section. These boundaries are enforced in code, not just in the agent's prompt.
